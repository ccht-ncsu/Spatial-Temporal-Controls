# make13.py
#
#
# Author: Nicole Arrigo 
# Last updated: 1.20.2026
# Unity ID: nkarrigo
# Purpose:  Using a polygon, determine the nodes in the fort.14 mesh within the desired region. 
# Then create a new nodal attribute in fort.13 file so SWAN can be run in selective regions and 
# with input boundary spectra. 
#
# INPUTS: fort.13, fort.14, hardcoded - polygon lon lat, if csv is provided. 
#
# Main Steps:
# Step 1: Get user inputs. 
#
# Step 2: Create polygons and convert to shapefiles.
#
# Step 3: Get fort.14 node and element data. Determine max boundary id and node neighbors.
#
# Step 4: Check each node with desired polygon.
#
# Step 5: Find internal source nodes. If csv not provided (using neighbor logic) and if csv is 
# provided (by finding the closest nodes to each given station location). 
# Case 1 would be used in with a full domain SWAN sim to output internal sources at 
# partial domain boundary nodes. Then, these internal sources would be identified in the fort.13 
# of the partial domain SWAN sim using SLC. Case 2 would be used with existing boundary spectra
# to be used as internal sources in a SLC simulation.  
#
# Step 6: Write new fort.13 with nodal attribute swan_local_control.
#
# Step 7: Write CSV file with internal source info. 
#
# Software Requirements: numpy, matplotlib, netCDF4, shapely, and geopandas must be installed.
#
# import libraries and packages
import numpy as np
import matplotlib.pyplot as plt
from netCDF4 import Dataset
import shapely
from shapely.prepared import prep
from shapely.geometry import Polygon, Point
import geopandas as gpd
import time
import csv

#------------------- Step 1: Get user inputs. 
start_1 = time.time()

# Define latitude and longitude coordinates of desired polygon
lon1 = [ -77.55, -68.43, -68.95, -82.39]
lat1 = [40.78, 36.20, 29.04, 32.07]

original_fort_13_file = f"fort.13"
# This will be used for your SLC Simulation
new_fort_13_file = f"fort_NC76.13"

# Change if csv is provided with desired input spectra /internal sources
#internal_source_csv = None  
internal_source_csv = "internal_sources.csv"

#end_1 = time.time()
#print(f"Step 1 (user inputs) time: {end_1 - start_1:.4f} seconds")

#---------------- Step 2: Create polygon and convert to shapefiles.
def create_polygon_shp(lon, lat):
    """
    Create a polygon shapefile from latitude and longitude coordinates.
    Parameters:
        lon (list): List of longitude coordinates.
        lat (list): List of latitude coordinates.
     Returns:
        Polygon: The created polygon.
    """
    # Create polygon from coordinates
    polygon_geom = Polygon(zip(lon, lat))

    # Create GeoDataFrame and save as shapefile
#    gdf_poly = gpd.GeoDataFrame(geometry=[polygon_geom])
#    gdf_poly.to_file(f"polygon{count}.shp")
#    print(f"Shapefile saved.")
    return polygon_geom

# Use function to create polygon from latitude and longitude coordinates
poly_fort = create_polygon_shp(lon1, lat1)

#end_2 = time.time()
#print(f"Step 2 (polygon) time: {end_2 - end_1:.4f} seconds")

#--------------------- Step 3: Get fort.14 node and element data. 
# Determine max boundary id and node neighbors
  
# Read mesh data from file
fort14 = []

node_list = []
element_list = []
boundary_nodes = set()

with open("fort.14", 'r') as file:
    next(file)  # skip header line 1
    second_line = next(file)  # skip header line 2

    num_elements, num_nodes = map(int, second_line.strip().split())

    # Read nodes
    for _ in range(num_nodes):
        line = file.readline()
        # Split the line into columns
        columns = line.strip().split()
        # Check if there are enough columns
        if len(columns) == 4:
            # Extract node number, x and y coordinates
            node_number = int(columns[0])
            x_coord = float(columns[1])
            y_coord = float(columns[2])
            # Append to nodes list
            node_list.append((node_number, x_coord, y_coord))
            # Debugging: Print data
            #print("Node Number:", node_number, "X Coordinate:", x_coord, "Y Coordinate:", y_coord)
        else:
            print(f"Skipping node line: {line.strip()}")
        
    #end_3a = time.time()
    #print(f"Step 3a (node table) time: {end_3a - end_2:.4f} seconds")
    # Read elements
    for _ in range(num_elements):
        line = file.readline()
        columns = line.strip().split()
        # Element table (Elem #, 3, Node1, Node2, Node3)
        if len(columns) == 5:
            element_number = int(columns[0])
            node1 = int(columns[2])
            node2 = int(columns[3])
            node3 = int(columns[4])
            element_list.append((node1, node2, node3))
        else:
            print(f"Skipping element line: {line.strip()}")
    #end_3b = time.time()
    #print(f"Step 3b (element table) time: {end_3b - end_3a:.4f} seconds")
    
    # Determine current number of boundary segments. Value+1 used as internal souce counter 
    # Read open boundaries
    NOPE = int(file.readline().split()[0])  # number of open boundary segments
    NETA = int(file.readline().split()[0])  # total open boundary nodes 

    for _ in range(NOPE):
        parts = file.readline().split()
        nums = [int(x) for x in parts if x.lstrip('-').isdigit()]
        NVDLL = nums[0]
        IBTYPEE = nums[1] if len(nums) > 1 else 0

        for _ in range(NVDLL):
            node_num = int(file.readline().split()[0])
            #boundary_nodes.add(node_num)

    # Read land boundaries
    NBOU = int(file.readline().split()[0])
    NVEL = int(file.readline().split()[0])

    for _ in range(NBOU):
        parts = file.readline().split()
        nums = [int(x) for x in parts if x.lstrip('-').isdigit()]
        NVELL = nums[0]
        IBTYPE = nums[1] if len(nums) > 1 else 0

        for _ in range(NVELL):
            node_num = int(file.readline().split()[0])
            #boundary_nodes.add(node_num)

    total_boundary_segments = NOPE + NBOU

# Convert node list to NumPy array and create a dictionary for lookup
node_dict = {node[0]: (node[1], node[2]) for node in node_list}
node_list = np.asarray(node_list)

#end_3c = time.time()
#print(f"Step 3c (added find boundaries) time: {end_3c - end_3b:.4f} seconds")

# Build a dictionary to store neighboring nodes
neighbors = {node[0]: set() for node in node_list}  # Initialize empty sets for each node

# Loop over the elements and record neighboring nodes
for node1, node2, node3 in element_list:
    neighbors[node1].update([node2, node3])  # Node1 connects to Node2 and Node3
    neighbors[node2].update([node1, node3])  # Node2 connects to Node1 and Node3
    neighbors[node3].update([node1, node2])  # Node3 connects to Node1 and Node2


#end_3d = time.time()
#print(f"Step 3d (neighbors) time: {end_3d - end_3c:.4f} seconds")

#--------------------- Step 4: Check each node with desired polygon.

prepared_poly = prep(poly_fort)

# Initialize a list to store node numbers within the polygon
nodes_within_polygon = []
# Initialize a list to store node numbers not within the polygon
nodes_not_within_polygon = []

node_numbers = np.array([int(item[0]) for item in node_list])
x_coords = np.array([float(item[1]) for item in node_list])
y_coords = np.array([float(item[2]) for item in node_list])

# Based on shapely 
if hasattr(shapely, "contains"):  # means vectorized API is available
    points = shapely.points(x_coords, y_coords)  # vectorized point creation
    mask = shapely.contains(poly_fort, points)   # boolean array
else:
    # backward compatible version
    mask = np.array([prepared_poly.contains(Point(x, y)) for x, y in zip(x_coords, y_coords)])

# Loop through the nodes and check if each is within the polygon


    # Check if the node is within the polygon

# Separate node numbers based on mask
nodes_within_polygon = node_numbers[mask].tolist()
nodes_not_within_polygon = node_numbers[~mask].tolist()

sorted_nodes = sorted(nodes_not_within_polygon)
nodes_not_within_polygon_set = set(nodes_not_within_polygon)

#print("Nodes within Polygon", nodes_within_polygon)
#print("ploy1", poly1)
#print("Nodes not within Polygon", nodes_not_within_polygon)
#print("Sorted", sorted)

#end_4 = time.time()
#print(f"Step 4 (points within poly) time: {end_3d - end_4:.4f} seconds")

#--------------------- Step 5: Find internal source nodes. If csv not provided (using neighbor 
# logic) and if csv is provided (by finding the closest nodes to each given station location). 
# Case 1 would be used in with a full domain SWAN sim to output internal sources at 
# partial domain boundary nodes. Then, these internal sources would be identified in the fort.13 
# of the partial domain SWAN sim using SLC. Case 2 would be used with existing boundary spectra
# to be used as internal sources in a SLC simulation.  

# function for closest node to each station
def find_closest_node_id(node_array, lon, lat):
    """
    node_array: Nx3 array [node_id, x, y]
    """
    dx = node_array[:, 1] - lon
    dy = node_array[:, 2] - lat
    idx = np.argmin(dx*dx + dy*dy)
    return int(node_array[idx, 0])

internal_source_nodes = []

if internal_source_csv is None:
    # case 1: NO CSV given by user so use active polygon and neighbor logic
    print("No CSV provided - finding internal source nodes using neighbor logic")
    internal_source_nodes = [
        node
        for node in nodes_within_polygon
        if neighbors[node] & nodes_not_within_polygon_set
    ]
else:
    # case 2: CSV provided - find nearest node to each station
    print(f"CSV provided ({internal_source_csv}) finding nearest node to each station")
    with open(internal_source_csv, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            station = row["Station"]
            lon = float(row["Longitude"])
            lat = float(row["Latitude"])
            nearest_node = find_closest_node_id(node_list, lon, lat)
            internal_source_nodes.append(nearest_node)
            print(f"  Station {station}: lon={lon}, lat={lat}, node {nearest_node}")

#print("Internal Boundary Nodes Identified:", internal_source_nodes)
#print("number of sources=",len(internal_source_nodes))


is_value_dict = {}
#end_5 = time.time()
#print(f"Step 5 (internal sources) time: {end_5 - end_4:.4f} seconds")


#--------------- Step 6: Write new fort.13 with nodal attribute swan_local_control. 
def update_fort_13(original_filename, new_filename, nodes_not_within_polygon, internal_sources):
    """
    Update the original fort.13 file to include the swan_local_control attribute, indicating 
    nodes that are active for SWAN and internal source nodes. 
    Parameters:
        original_filename (string): the fort.13 file from original simulation.
        new_filename (string): the name of the fort.13 file for the new SLC simulation.
        nodes_not_within_polygon (set): Set of nodes that will be set to a non-default value for SLC.
        internal_sources (list): List of nodes along the edge of new SWAN domain that will have spectra 
            applied as boundary conditions at. 
    """
    with open(original_filename, 'r') as original_file:
        lines = original_file.readlines()

    # Update the third line by incrementing the value
    num_attr = int(lines[2].strip())
    lines[2] = str(num_attr + 1) + '\n'

    # Find the last line of the heading assuming 3 header lines followed by 4 lines for each attr 
    lastline_heading = 2 + 4 * num_attr 
    # Insert 'swan_on', '1', '1' after 'sea_surface_height_above_geoid' and '0' removed space
    lines.insert(lastline_heading + 1, 'swan_local_control\n')
    lines.insert(lastline_heading + 2, ' 1\n')
    lines.insert(lastline_heading + 3, ' 2\n')
    lines.insert(lastline_heading + 4, ' 1 0\n')

    # Add a line to end of file before looping through nodes
    lines.append('swan_local_control\n')  # Add "swan_on" line

    # Convert internal sources list to a set for quick lookup
    # change this later - fixes to spc we have
    internal_sources = set(int(node) for node in internal_source_nodes)
    # internal_source_nodes = set(int(node) for node in internal_boundary_nodes)

    # Create a sorted list of all nodes needing to be marked (0 or -1)
    #    all_nodes = sorted(set(nodes_not_within_polygon) | internal_source_nodes)
    all_nodes = sorted(set(nodes_not_within_polygon) | set(internal_source_nodes))
    lines.append(f" {len(all_nodes)}\n")  # Add total number of nodes

    # Initialize counter for internal source numbering
    # 7c changed 
    internal_source_count = total_boundary_segments + 1

    for node in all_nodes:
        # if node in internal_source_nodes:
        if node in internal_source_nodes:
            so_value = 1
            is_value = internal_source_count
            internal_source_count += 1
        else:
            so_value = 0
            is_value = 0
            # Store is_value 
        is_value_dict[node] = is_value

        lines.append(f" {node} {so_value} {is_value}\n")

    # Write the modified content to the new file
    with open(new_filename, 'w') as new_file:
        new_file.writelines(lines)

update_fort_13(original_fort_13_file, new_fort_13_file, sorted_nodes, internal_source_nodes)
#end_6 = time.time()
#print(f"Step 6 (new fort.13) time: {end_6 - end_5:.4f} seconds")

nodes_within_polygon_set = set(nodes_within_polygon)
internal_source_nodes_set = set(internal_source_nodes)

internal_sources = np.array(
    [
        (int(node_number), float(x_coord), float(y_coord), f"spec{int(node_number)}.spc")
        for node_number, x_coord, y_coord in node_list
        if node_number in nodes_within_polygon_set and node_number in internal_source_nodes_set
    ],
    dtype=object
)
#--------------- Step 7: Write CSV file with internal source info 
if internal_source_csv is None:
    csv_filename = "station_locations.csv"
    # Open the file for writing
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        # Write header
        writer.writerow(["Station", "Longitude", "Latitude"])    
        for entry in internal_sources:
            node, lon, lat, _ = entry
            writer.writerow([node, lon, lat])
    print(f"CSV file '{csv_filename}' created with {len(internal_sources)} entries.")


