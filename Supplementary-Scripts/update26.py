# %%
# =============================================================
# Station-to-PE mapper
#
# This script determines which ADCIRC mesh element and partition (PE) owns
# each observation station based on longitude/latitude coordinates. It also
# generates per-PE fort.26 files (and optionally a combined global fort.26)
# with the appropriate POINTS and SPECOUT entries for each station.
#
# Required files in the working directory:
#  - fort.14         : ADCIRC mesh file describing nodes and elements
#  - partmesh.txt    : partition mapping for mesh nodes (PE assignment)
#  - station_locations.csv : CSV with station_id, longitude, latitude
#  - fort.26         : template fort.26 used for assembling outputs
#
# Outputs:
#  - pe_output.csv   : CSV mapping each station to its assigned PE folder
#  - PE####/fort.26   : one fort.26 per PE folder containing that PE's stations
#  - global_fort.26  : (optional) combined fort.26 containing all POINTS/SPECOUT
# =============================================================

# Standard library and typing imports
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import glob
from typing import List, Tuple, Iterable, Optional, Dict
import warnings # CAN 
import csv
import heapq
import time
from contextlib import contextmanager
import os
import sys

# =========== File Paths ===========
FORT14_PATH = "fort.14" 
PARTMESH_PATH = "partmesh.txt" 
STATION_CSV_PATH = "station_locations.csv"
PE_OUTPUT_PATH = "pe_output.csv"
UPDATE_FORT26_PATH = "fort.26"
BASE_FORT26_PATH = UPDATE_FORT26_PATH

# =========== Timer Feature ===========
ENABLE_TIMING = True  # Set to False to disable timing output

# =========== Inputs (can be overridden via CLI) ===========
PRINT_GLOBAL_FORT26 = False
FORT26_DATE = None
FORT26_TIMESTEP = 1800
FORT26_SPEC_DIM = "2D"



def str2bool(s: str) -> bool:
   """Convert a user-provided string to a boolean.

   Accepts common truthy/falsy tokens (case-insensitive):
   - True:  'true', '1', 'yes'
   - False: 'false', '0', 'no'

   Raises ValueError for any unrecognized value.
   """
   s = s.strip().lower()
   if s in ("true", "1", "yes"):
      return True
   if s in ("false", "0", "no"):
      return False
   raise ValueError(f"Cannot convert '{s}' to boolean. Use true/false, 1/0 or yes/no.")

def start_up():
   """Parse and validate command-line inputs, initializing global variables.

   Supported inputs (positional or flags):
     - FORT26_DATE (required)
     - PRINT_GLOBAL_FORT26 (boolean)
     - FORT26_TIMESTEP (integer seconds)
     - FORT26_SPEC_DIM ("1D" or "2D")

   The function updates the module-level variables and will exit with an
   explanatory message if required values are missing or invalid.
   """
   argv = sys.argv[1:]
   if not argv:
      return
   if argv[0] in ("-h", "--help"):
      print("Usage:\n  Positional: script.py FORT26_DATE [PRINT_GLOBAL] [TIMESTEP] [SPEC_DIM]\n  " \
            "Flags: script.py --date=DATE --global_fort26=true --timestep=1800 --spec_dim=2D")
      sys.exit(0)

   # Inner single-pass parser (kept local to start_up)
   def init_inputs(argv=None):
      global PRINT_GLOBAL_FORT26, FORT26_DATE, FORT26_TIMESTEP, FORT26_SPEC_DIM, BASE_FORT26_PATH
      if argv is None:
         argv = sys.argv[1:]

      if not argv:
         if FORT26_DATE is None:
            raise SystemExit("FORT26_DATE must be provided (positional or --date=...).")
      else:
         if not argv[0].startswith("--"):
            try:
               FORT26_DATE = float(argv[0])
            except Exception:
               raise SystemExit(f"Invalid fort26_date: {argv[0]}")
            if len(argv) > 1:
               PRINT_GLOBAL_FORT26 = str2bool(argv[1])
            if len(argv) > 2:
               FORT26_TIMESTEP = int(argv[2])
            if len(argv) > 3:
               if argv[3] not in ("1D", "2D"):
                  raise SystemExit(f"Invalid fort26_spec_dim: {argv[3]}")
               FORT26_SPEC_DIM = argv[3]
         else:
            for token in argv:
               if not token.startswith("--"):
                  continue
               if "=" in token:
                  k, v = token.split("=", 1)
               else:
                  k, v = token, "true"
               
               key = k.lstrip("-").replace('-', '_').lower()
               if key in ("print_global_fort26", "global_fort26", "global", "print_global"):
                  PRINT_GLOBAL_FORT26 = str2bool(v)
               elif key in ("fort26_date", "date"):
                  try:
                     FORT26_DATE = float(v)
                  except Exception:
                     raise SystemExit(f"Invalid fort26_date: {v}")
               elif key in ("fort26_timestep", "timestep", "time_step"):
                  try:
                     FORT26_TIMESTEP = int(v)
                  except Exception:
                     raise SystemExit(f"Invalid fort26_timestep: {v}")
               elif key in ("fort26_spec_dim", "spec_dim", "specdim"):
                  if v not in ("1D", "2D"):
                     raise SystemExit(f"Invalid fort26_spec_dim: {v}")
                  FORT26_SPEC_DIM = v

      if FORT26_DATE is None:
         raise SystemExit("FORT26_DATE is required.")

   # Call unified parser and validate
   init_inputs(argv)
   return

# =============================================================
# Data Classes
# =============================================================
# Data classes provide convenient, typed containers for nodes/elements/PEs
@dataclass(frozen=True)
class Node:
   id: int
   lon: float
   lat: float

@dataclass(frozen=True)
class Element:
   id: int
   n1: int
   n2: int
   n3: int

# `field(default_factory=list)` ensures each PE instance gets its own lists
@dataclass()
class PE:
   pe_id : int
   station_ids: List[str] = field(default_factory=list)
   POINTS_lines: List[str] = field(default_factory=list)
   SPECOUT_lines: List[str] = field(default_factory=list)


@contextmanager
def timer(label: str):
   if not ENABLE_TIMING:
      yield
      return
   t0 = time.perf_counter()
   try:
      yield
   finally:
      dt = (time.perf_counter() - t0)
      print(f"[TIMER] {label}: {dt:.1f} s")


# %%
# =============================================================
# fort.14 File Parser
# =============================================================
def load_fort14(path: str) -> Tuple[List[Node], List[Element], Dict[int, List[Element]]]:
   """
   Read a fort.14 mesh file and return nodes, elements, and a node->elements map.

   Arguments:
      path: Path to the fort.14 file.
   """
   with timer(f"fort.14 open {path}"):
      nodes: List[Node] = []
      elements: List[Element] = []
      node_to_elements: Dict[int, List[Element]] = defaultdict(list)

      # Open `fort.14` for reading
      with open(path, "r") as f:
         _ = f.readline()        
         np_ne = f.readline().split()     # splits up each line into a new row in the list

         if len(np_ne) < 2: 
            raise ValueError("Could not read NP/NE from line 2.")
         
         NE, NP = int(np_ne[0]), int(np_ne[1])  # grabs the # of elements and then # of nodes - CONFIRM

         print(f"Number of nodes: {NP}")
         print(f"Number of elements: {NE}")

            # ========== Parse nodes ==========
         with timer(f"parse nodes (NP={NP})"):
            for _ in range(NP):
               parts = f.readline().split()
               # parts: node_id, lon, lat, [z]
               nid, lon, lat = int(parts[0]), float(parts[1]), float(parts[2])
               # creates the an instance of node class and appends to list
               nodes.append(Node(id=nid, lon=lon, lat=lat))
            
         # ========== Parse elements ==========
         with timer(f"parse elements (NE={NE})"):
            for _ in range(NE):
               parts = f.readline().split()
               # element id, #of nodes, node 1, node 2, node 3
               eid  = int(parts[0])
               ncount = int(parts[1])
               
               if ncount != 3:
                  # Should always be 3, but to double check; we only allow triangles
                  warnings.warn(f"Element {eid} has node_count={ncount}; skipping (triangles only).")
                  continue
               # Gathering nodes
               n1, n2, n3 = int(parts[2]), int(parts[3]), int(parts[4])
               
               # creates the an instance of element class and appends to list
               e = Element(id=eid, n1=n1, n2=n2, n3=n3)
               elements.append(e)

               # build node_to_elements
               node_to_elements[n1].append(e)
               node_to_elements[n2].append(e)
               node_to_elements[n3].append(e)
      return nodes, elements, node_to_elements                    


# %%
# =============================================================
# Find the k Nearest Nodes to a given (by lon/lat) point
# =============================================================
def k_nearest_node_ids_lonlat(nodes: List[Node], p_lon: float, p_lat: float, k:int) -> Tuple[List[int], bool]:
   """Return the IDs of the k nearest nodes to a point (lon, lat).

   Arguments:
      nodes: Sequence of Node objects to search.
      p_lon, p_lat: Longitude and latitude of the query point.
      k: Maximum number of nearest nodes to return (e.g. 20).

   Returns:
      A tuple (list_of_node_ids, closest_within_threshold_flag).
   """

   def distance(n: Node) -> float: 
      return (n.lon - p_lon)**2 + (n.lat - p_lat)**2
   
   #nearest = sorted(nodes, key=d2)[:min(k, len(nodes))]
   k = min(k, len(nodes))
   
   """Return a list with the n smallest elements from the dataset 
   defined by iterable. key, if provided, specifies a function of one
   argument that is used to extract a comparison key from each element in iterable"""
   nearest = heapq.nsmallest(k, nodes, key=distance)

   # Debug/logging output showing nearest nodes (can be verbose)
   # print(f"\t Found {k} closest nodes.")
   # for n in nearest:
   #    print(f"   Node ID {n.id}: lon={n.lon}, lat={n.lat}")

   # Determine if the closest node is within threshold in both lon and lat
   closest_within_thresh = False
   if nearest:
      closest = nearest[0]
      thresh = 1e-5
      if abs(closest.lon - p_lon) <= thresh and abs(closest.lat - p_lat) <= thresh:
         closest_within_thresh = True

   # Return node ids and a boolean indicating whether the nearest node
   # is effectively coincident with the query point (within threshold).
   return [n.id for n in nearest], closest_within_thresh

# %%
# =============================================================
# Find Elements Touching Nearest Nodes 
# =============================================================
def elements_touching_nodes(node_to_elements: Dict[int, List[Element]], node_ids: List[int]) -> List[Element]:
   """
      Find Elements Touching Nearest Nodes 
      Returns all elements that share at least one of the given node IDs.

      Arguments:
         node_to_elements: Dictionary of nodes and the elements that a given node is apart of
         node_ids: List of all the nodes
   """
   seen = set()
   nearest_elements : List[Element] = []
   
   for nid in node_ids:
      for e in node_to_elements.get(nid, []):
         if e.id not in seen:
            seen.add(e.id)
            nearest_elements.append(e)
   
   # print checks
   print(f"\t Finding the {len(nearest_elements)} closest elements are.")
   return nearest_elements

# %%
# =============================================================
# Pick Element by Centroid Distance
# =============================================================
def pick_by_centroid_lonlat(
      elements: List[Element], 
      id_to_node:Dict[int, Node],  
      p_lon: float, p_lat:float
) -> Optional[Element]:
   """Select the element whose centroid is closest to the query point.

   For each candidate triangular element, compute the centroid and return the
   element with the smallest squared distance to (p_lon, p_lat). If an element
   references a node that is missing in `id_to_node`, that element is skipped
   with a warning.
   """
   def centroid_lonlat(ax: float, ay: float, bx: float, by: float, cx: float, cy: float):
      return ((ax + bx + cx) / 3.0, (ay + by + cy) / 3.0)
      
   best = None
   best_d2 = float("inf")

   for e in elements: 
      # skip if any node ID is missing from the node dictionary
      if e.n1 not in id_to_node or e.n2 not in id_to_node or e.n3 not in id_to_node:
         warnings.warn(f"Element {e.id} does not have a node in the nearest node list.")
         continue
      
      A, B, C = id_to_node[e.n1], id_to_node[e.n2], id_to_node[e.n3]
      cx, cy = centroid_lonlat(A.lon, A.lat, B.lon, B.lat, C.lon, C.lat) 
      
      d2 = (cx - p_lon)**2 + (cy -p_lat)**2

      
      if d2 < best_d2:
         best_d2, best = d2, e   
   return best

# %%
# =============================================================
# Geometry Utilities
# =============================================================
def twice_area(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float:
   """Compute twice the signed area of triangle ABC using a 2D cross product."""
   def cross2(ax: float, ay: float, bx: float, by: float) -> float:
      return ax * by - ay * bx
   return abs(cross2(bx-ax, by-ay, cx-ax, cy-ay))

def point_in_element(px: float, py: float, 
                     ax: float, ay: float,
                     bx: float, by: float,
                     cx: float, cy: float,
                     eps: float) -> bool:
   """Return True if point P(px,py) is inside triangle ABC within tolerance.

   This uses an area-comparison method: if the sum of areas of sub-triangles
   (PAB, PBC, PCA) equals the total triangle area (ABC) within `eps`, the point
   is considered inside. Returns False if the base triangle has zero area.
   """
   AT = twice_area(ax, ay, bx, by, cx, cy)
   if AT == 0.0:
      return False
   A1 = twice_area(px, py, ax, ay, bx, by)
   A2 = twice_area(px, py, bx, by, cx, cy)
   A3 = twice_area(px, py, cx, cy, ax, ay)

   matches = ((A1 + A2 + A3) - AT) <= eps
   if not matches:
      print(f"Total area (AT): {AT}")
      print(f"Sum of sub-areas (A1+A2+A3): {A1 + A2 + A3}")
   return matches

# %%
# =============================================================
# Find Element Containing Station
# ============================================================= 
def find_element_for_station(
   station_lon: float,
   station_lat: float, 
   nodes: List[Node], 
   id_to_node: Dict[int, Node], 
   node_to_elements: Dict[int, List[Element]],  
   station_id: str,
   k_list: Iterable[int] = (20, 30, 40, 500),
   ) -> Tuple[Optional[Element], Optional[str], bool, Optional[int]]:
   """Locate the mesh element that contains a station's coordinate.

   This function uses a few strategies:
     1. Find k nearest nodes to the station point.
     2. Collect elements that touch those nodes.
     3. Select the element whose centroid is closest to the station.
     4. Verify the point lies inside the chosen element; if not, expand
        the neighborhood (increase k) and retry.

   Arguments:
      station_lon, station_lat: Query point coordinates.
      nodes, id_to_node, node_to_elements: Mesh structures loaded from fort.14.
      station_id: Station identifier (used for logging).
      k_list: Sequence of k-values to try (e.g. (20,30,40,500)).

   Returns:
      (element_or_None, maybe_station_id_for_reporting, closest_node_flag, closest_node_id)
   """
      
   eps = 1e-5
   n = 0
   
   with timer(f"find_element_for_station station={station_id}"):
      for k in k_list:
            # cand_node_ids: IDs of the k nearest nodes
         with timer(f"K nearest nodes (k={k})"):
            cand_node_ids, closest_node_within_thresh = k_nearest_node_ids_lonlat(nodes, station_lon, station_lat, k)
            closest_node_id = cand_node_ids[0] if cand_node_ids else None
            if closest_node_within_thresh:
               print(f"    Closest node {closest_node_id} is within threshold of the station point.")
               # Return early indicating a near-node match (no enclosing element chosen)
               return None, None, True, closest_node_id
         
         
         # cand_elems: elements that touch the candidate nodes
         with timer(f"touching element (k={k})"):
            cand_elems = elements_touching_nodes(node_to_elements, cand_node_ids)

         # If no elements found, go to next k in k_list         
         if not cand_elems:
            # warnings.warn(f"No Elements found in the {k} closest nodes")
            continue
   
         # chosen_element: pick the element whose centroid is closest to the point
         with timer(f"pick centroid (k={k}), elems={len(cand_elems)}"):
            chosen_element = pick_by_centroid_lonlat(cand_elems, id_to_node, station_lon, station_lat)
         
         # If no close element found, go to next k in k_list
         if not chosen_element:
            # warnings.warn(f"No chosen element found in the {k} closest nodes")
            continue
         
         
         # Check whether the chosen element actually contains the station
         A, B, C = id_to_node[chosen_element.n1], id_to_node[chosen_element.n2], id_to_node[chosen_element.n3]

         print("closest element:", chosen_element)
         print(f"Checking to see if element #{chosen_element.id} holds the station...")

         with timer(f"point_in_element (k={k}) eps={eps:g}"):
             inside = point_in_element(px=station_lon, py=station_lat, 
                                       ax=A.lon, ay=A.lat, bx=B.lon, 
                                       by=B.lat, cx=C.lon, cy=C.lat, eps= eps)
         if inside:            
            print(f"    element #{chosen_element.id} does hold the station. Element is found.")
            large_sid = station_id if eps >= 1e-3 else None
            return chosen_element, large_sid, False, None
         else:
            print(f"    element #{chosen_element.id} does NOT holds the station.")
            print(f"    Printing out {len(cand_elems)} of the closest elements:")
            print(f"    ===== CHECKING PRINT: =====")
            for e in cand_elems:
               print(f"       Element ID {e.id}: node1={e.n1}, node2={e.n2}, node3={e.n3}")
            if n < len(k_list):
               print(f"       Increasing the number of nodes from {k_list[n]} to {k_list[n+1]}")
               print(f"       Increasing margin of error from {eps} to {eps*10}")
               n += 1
               eps *= 10
      return None, None, False, None

# %%
# ============================================================= 
# find_pe_for_station
# ============================================================= 
def find_pe_for_station(
      station_lon: float,
      station_lat: float,
      nodes: List[Node],
      id_to_node: Dict[int, Node],
      node_to_elements: Dict[int, List[Element]],
      station_id: str,  
      partmesh: List[int],      
) -> Tuple[Optional[int], Optional[str]]:
      """Determine which PE folder owns the element containing the station.

      Strategy:
        - Find the element that contains the station (or a nearby node).
        - If the station lies on/near a node, use the node's PE assignment.
        - Otherwise, inspect the three nodes of the chosen element and use a
          majority vote to decide the PE (helps with ghost/partition-edge cases).

      Arguments:
         station_lon, station_lat: Query point coordinates.
         nodes, id_to_node, node_to_elements: Mesh structures.
         station_id: Station identifier used for logging.
         partmesh: List mapping node index -> PE folder number.
      """
      # Find which element the station is in
      with timer(f"find_pe_for_station station={station_id}"):
         print("Looking up PE assignment for station")
         element, maybe_sid, closest_within_thresh, closest_node_id = find_element_for_station(station_lon, station_lat, nodes, id_to_node, node_to_elements, station_id)
            # If the station is essentially on a node, return the PE that owns that node directly
         if closest_within_thresh and closest_node_id is not None:
            pe_for_station = partmesh[closest_node_id - 1]
            print(
               f"================ Station on Node ================",
               f"\n  Station is on/very near node {closest_node_id}",
               f"\n  Assigning PE {pe_for_station} based on that node.")
            return pe_for_station, None
         if not element:
            warnings.warn("We cannot determine which element you station is in. Please confirm lat and lon.")
            return None, None
         else:
            # Log the chosen element and its nodes for traceability
            if element:
               print(
                  "============ Closest Element ============",
                  f"\n  Closest Element ID: {element.id}",
                  f"\n  Node 1: {element.n1}",
                  f"\n  Node 2: {element.n2}",
                  f"\n  Node 3: {element.n3}")
   
      # Read the partmesh.txt file         
      with timer("PE votes (Counter)"):                     
         # Look up which PE each node of the element belongs it         
         node_ids = [element.n1, element.n2, element.n3]
         pe_numbers = []
         for nid in node_ids:                  
               pe_number = partmesh[nid -1]
               pe_numbers.append(pe_number)
               
         # if the three PE numbers are not all equal we have a ghost-node
         unique_pes = set(pe_numbers)
         if len(unique_pes) > 1:
               print(f"   WARNING: station {station_id} element {element.id} nodes span multiple PEs: {pe_numbers}")
               # specifically warn if there is no majority (all three different)
               if len(unique_pes) == 3:
                     print(f"      >> No majority vote – all three nodes in distinct PEs")
         
         # counts the amount of PE folder - helpful for ghost node
         #     eg. {25,3} --> three nodes in PE folder 25
         pe_counter = Counter(pe_numbers)

         # Grabs PE folder that has the most nodes are in.
         #     Helpful for ghost nodes as the element is in the PE folder has 2 nnodes in that folder. 
         pe_for_station = pe_counter.most_common(1)[0][0]

         print("============ PE Folder ============", 
         "\n    Station Lon: ", station_lon,
         "\n    Station Lat: ", station_lat ,
         "\n    PE Folder: ", pe_for_station)
         for i in range(len(node_ids)):
               print(f"    Node {i} → PE{pe_numbers[i-1]:04d}")

         return pe_for_station, maybe_sid

# %%
def update_fort26(stations_pes_path:str, starting_fort26_path:str, update_fort26_path:str,
                  writing_global_fort: bool, date:float, timestep:int, dim:str):
   """Assemble per-PE and optional global fort.26 files from station->PE mapping.

   Arguments:
      stations_pes_path: CSV path mapping station IDs to PE folders.
      starting_fort26_path: Template fort.26 used as a base for insertion.
      update_fort26_path: Relative filename to write into each PE folder.
      writing_global_fort: If True, also write a combined global fort.26.
      date: Start date value to include in SPECOUT entries.
      timestep: Timestep (seconds) to include in SPECOUT entries.
      dim: Spectral dimension, e.g. '1D' or '2D'.
   """
   pe_groups: Dict[int, PE] = {} # key: pe_id, value: PE dataclass instance
   


   def points_line_format(name: str, x: float, y: float,) -> str:
      """Format a POINTS line for fort.26.

      Returns a single-line string containing the station identifier and
      coordinates formatted to six decimal places.
      """
      return f"POINTS '{name}' {x:.6f} {y:.6f}\n"
   
   def specout_line_format(name: str, start_date: float, timestep: int, dim: str) -> str:
      """Format a SPECout line for fort.26.

      Args:
         name: Station identifier (matches POINTS entry).
         start_date: Numerical start date value included in the SPECOUT line.
         timestep: Time step in seconds.
         dim: Spectral dimension ('1D' or '2D').
      """
      return f"SPECout '{name}' SPEC{dim} ABSolute S '{name}.spc' OUTput {start_date:.6f} {timestep} Sec\n"
         

   with timer("read station PE CSV"):
      with open(stations_pes_path, "r", newline="") as f:
         reader = csv.DictReader(f)
         for row in reader:
            pe_id = int(row["PE_Folder"])
            curr = pe_groups.setdefault(pe_id, PE(pe_id=pe_id))            

            sid = f"bnd{row['Station_ID']}".strip()
            #sid = f"bnd{row['sid']}"
            x = float(row['longitude'])
            y = float(row['latitude'])
            

            curr.station_ids.append(sid)
            curr.POINTS_lines.append(points_line_format(sid, x, y))
            curr.SPECOUT_lines.append(specout_line_format(sid, date, timestep, dim))

      if not pe_groups:
         raise ValueError("No stations found in CSV!")
   

   global_lines: List[str] = []
   test_index = None
   star_index = None


   # Read the template fort.26 and locate insertion anchors
   with timer("read base fort.26 and locate insertion anchors"):
      with open(starting_fort26_path, "r") as reading_file:
         lines = reading_file.readlines()

         # Looks for NUM STOPC DABS and a $******* each line
         for i, line in enumerate(lines):
            if '$*************************************************************' in line:
               star_index = i
            if 'TEST' in line:
               test_index = i
      if star_index is None or test_index is None:
         raise RuntimeError("Could not find anchors ($**** and TEST) in base fort.26")
      

   def assemble_fort26_lines(template_lines, points: List[str], specs: List[str], star_index: int, test_index: int) -> List[str]:
      """Compose fort.26 content by inserting POINTS and SPECOUT blocks into template."""
      out: List[str] = []
      out.extend(template_lines[:star_index+2])
      out.extend(points)
      out.append('$\n')
      out.extend(specs)
      out.append('$\n')
      out.extend(template_lines[test_index:])
      return out
   
   def write_file(path: str, lines: List[str]) -> None:
      """Write the provided lines to `path` (overwrites if exists)."""
      with open(path, "w") as wf:
         wf.writelines(lines)


   #==== For the GLOBAL fort.26 ====
   if writing_global_fort:
      with timer("Assembling and Writing into Global fort.26 file"):
         sorted_ids = sorted(pe_groups)

         all_points = [
            line
            for pe_id in sorted_ids
            for line in pe_groups[pe_id].POINTS_lines
         ]

         all_specs = [
            line
            for pe_id in sorted_ids
            for line in pe_groups[pe_id].SPECOUT_lines
         ]

         global_fort26_path = "global_"+update_fort26_path
         global_lines = assemble_fort26_lines(lines, all_points, all_specs, star_index, test_index)
         write_file(global_fort26_path, global_lines)
         print(f" Wrote the combined fort.26 for all PEs --> {global_fort26_path}")

   #==== For the local PE fort.26 (s) ====
   with timer("Writing the fort.26 files for each PE folder"):
      # loops through a sort pe_groups folder
      for pe_id, group in sorted(pe_groups.items()):
         pe_lines = assemble_fort26_lines(lines, group.POINTS_lines, group.SPECOUT_lines,star_index, test_index)
         
         pe_dir = f"PE{pe_id:04d}"
         if not os.path.isdir(pe_dir):
            raise FileNotFoundError(f"Folder {pe_dir} not found in current directory")
         
         curr_path = os.path.join(pe_dir, update_fort26_path)
         write_file(curr_path, pe_lines)
         print(f"[PE {pe_id:04d}] Wrote {update_fort26_path} into {curr_path} folder.")
            

# %% 
# For reading the csv file
def get_value(row, *possible_keys):
   """Return the first matching value from `row` for any of the provided keys.

   The lookup is case-insensitive and supports multiple alternative header names
   (e.g. get_value(row, 'lon', 'longitude')). Raises KeyError if none match.
   """
   row_lower = {k.lower(): v for k, v in row.items()}
   for key in possible_keys:
      key = key.lower()
      if key in row_lower:
         return row_lower[key]
   raise KeyError(f"None of the keys {possible_keys} found in CSV header.")






# %%
def process_all():
   with timer("COMPLETE RUNNING TIME"):
      # BASE_FORT26_PATH has been validated in start_up()/run()
      print(f"Using the base fort.26 file: {BASE_FORT26_PATH}")

      with timer("Reading Fort.14"):
         nodes, elements,node_to_elements = load_fort14(FORT14_PATH)
         id_to_node = {n.id: n for n in nodes}



      with timer("read partmesh.txt once"):
         with open(PARTMESH_PATH, "r") as f:
            partmesh = [int(line.strip()) -1 for line in f]

      lines_out = []
      stations_w_no_pe = []
      stations_w_large_eps = []
      with timer("process stations CSV"):
         with open(STATION_CSV_PATH, "r", newline="") as f:
            reader = csv.DictReader(f)
            # normalize the headers
            reader.fieldnames = [name.lower() for name in reader.fieldnames]

            for row in reader:
                  sid = get_value(row,"station_id","station")
                  lon = float(get_value(row, "lon", "longitude"))
                  lat = float(get_value(row, "lat", "latitude"))
                  print(f"\n\n==========Testing for Station ID{sid}==========",
                        f"\nLongitude: {lon}      Latitude: {lat}")
                                          
                  pe_number, large_esp = find_pe_for_station(station_lon=lon, station_lat=lat,
                                       nodes=nodes, id_to_node=id_to_node, node_to_elements=node_to_elements, station_id=sid, 
                                       partmesh=partmesh)
                  if large_esp != None:
                     stations_w_large_eps.append(large_esp)               
                  if pe_number == None:
                     stations_w_no_pe.append(sid)   #(f"{sid},{lon},{lat}\n")
                     continue
                  S = {"sid":sid, "lon":lon, "lat":lat, "pe_id":pe_number}
                  lines_out.append(f"{S['sid']},{S['lon']},{S['lat']},{S['pe_id']:04d}\n")               
      
      with timer("write pe_output.csv"):
         with open(PE_OUTPUT_PATH, "w") as out:
               out.writelines("Station_ID,longitude,latitude,PE_Folder\n")
               out.writelines(lines_out)

      # ========== OUTPUT PRINT STATEMENTS ==========
      print(f"Wrote {len(lines_out)} lines to {PE_OUTPUT_PATH}")
      print(f"\n\n================WARNINGS================")
      print(f"There are {len(stations_w_no_pe)} Stations with issues in not finding pe_number. ")
      print(f"       There stations include: {stations_w_no_pe}")
      print(f"There are {len(stations_w_large_eps)} stations that use a margin of error than was greater than 0.001:")
      print(f"       There stations include: {stations_w_large_eps}")
      
      with timer("Updating the Fort.26 File(s)"):
         update_fort26(PE_OUTPUT_PATH, BASE_FORT26_PATH, UPDATE_FORT26_PATH,
                       PRINT_GLOBAL_FORT26, FORT26_DATE, FORT26_TIMESTEP, FORT26_SPEC_DIM)


if __name__ == "__main__":
   start_up()
   process_all()


