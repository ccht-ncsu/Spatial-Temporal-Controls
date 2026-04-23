# update26.py - Spectral Output & PE Station Mapping

**Authors:** Nicole Arrigo, Katherine Couch \
**Last Updated:** March 11, 2026 

---

## Overview
This script can be used to efficiently output spectral files. Given a list of station coordinates, it identifies which ADCIRC Processing Element (PE) partition contains each station and creates localized SWAN input files (`fort.26`) for each parallel partition. This ensures that each partition only contains the commands to export wave spectra at the stations physically located within its sub-domain.

---

## Intended Use Cases
- Outputting wave spectra from an ADCIRC+SWAN simulation using a CSV of stations and their locations.
   - This is useful when outputting spectral files for any use.
   - Also used for outputting spectra from a full domain simulation for 'boundary nodes' of a partial domain. 
---

## Expected Results

The following image displays a decomposed mesh domain and a series of stations where the user intends to output wave spectra. Each partition would receive it's own set of local `SPECout` commands corresponding to the stations contained in that partition.  

<img width="1716" height="600" alt="Untitled (5 72 x 2 in) (1)" src="https://github.com/user-attachments/assets/e2be79eb-1dc4-4033-ab08-9f2e9cdb375a" />

*Figure 1. Stations within different mesh partitions. Each station would have spectral output commands placed in the local SWAN input files for each partition.*

---
## Operational Modes

The script can be executed via the command line with flexible argument passing:

1. **Positional Mode:** `python update26.py [DATE] [PRINT_GLOBAL] [TIMESTEP] [SPEC_DIM]`
   > *Example:*   `python update26.py 20181006.000000 true 1800 2D`
   
2. **Flag Mode:** `python update26.py --date=0.0 --global=true --timestep=1800 --spec_dim=2D`
   > *Example:*    `python update26.py --date=20181006.000000`

*Note: `DATE` is a required input.*


---

## Inputs

### Required Files
- `fort.14` – ADCIRC mesh file (nodes and elements).
- `partmesh.txt` – Partition mapping file (links node IDs to PE numbers).
- `station_locations.csv` – Input coordinates. Expected format:
  ```csv
   Station,Longitude,Latitude
   16941,-76.334461,30.757137
   17172,-76.62709,30.970871
  ```
- `fort.26` – Template file used as the base for the header and insertion anchors.

### Parameters
- **Date (`--date`):** The numerical start date for SPECOUT entries (REQUIRED).
- **Global Printing (`--global`):** Boolean to determine if a combined `global_fort.26` is created (Default: False).
- **Timestep (`--timestep`):** Spectral output interval in seconds (Default: 1800).
- **Dimension (`--spec_dim`):** Spectral dimension, either `1D` or `2D` (Default: 2D).
---

## Outputs

**PE Output CSV (`pe_output.csv`)**
  - Lists each station with its assigned PE folder.
  - Contains: `Station_ID`, `Longitude`, `Latitude`, `PE_Folder`.
  
    Expected format:
    ```csv
    Station_ID,longitude,latitude,PE_Folder
    16941,-76.334461,30.757137,0011
    17172,-76.62709,30.970871,0008
    ```
    
**Local `fort.26` Files**
  - Written to `PE####/fort.26` folders.
  - Contains localized `POINTS` and `SPECOUT` blocks.

      Examples of new lines added: 
      ```
      POINTS 'bnd16941' -76.334461 30.757137
      ...
      SPECout 'bnd16941' SPEC2D ABSolute S 'bnd16941.spc' OUTput 20181006.000000 1800 Sec
      ```

**(Optional) Global `fort.26`**
  - Includes all `POINTS` and `SPECOUT` lines combined into one file.
  - Only created if `--global` variable set to `True`

---

## Methodology

The following steps describe how the script works internally. To run the script, the user only needs to first run adcprep to decompose the mesh and then run update26.py with the station_locations.csv file and specified parameters. The script will automatically write and move the commands to local SWAN input files.  

The following steps describe how the script operates internally. To run the script, the user must first execute `adcprep` to decompose the mesh, and then run `update26.py` using the `station_locations.csv` file along with the specified parameters. The script will automatically generate and insert the required commands into the local SWAN input (`fort.26`) files.

### Step 1: Read Mesh Files
- Reads `fort.14` to load node coordinates and construct element-to-nodes connectivity.
- Creates a reverse-lookup dictionary of elements connected each node.
- Reads `partmesh.txt` to determine which PE each node belongs to.

*Steps 2-4 are repeated for each station:*

### Step 2: Nearest Node Search
- Identifies the $k$ nearest nodes using a priority queue (`heapq`).

### Step 3: Identify Containing Element
- Uses the nearby nodes to collect candidate elements.
- Computes the centroid of each candidate element and selects the element whose centroid is closest to the station.
- Verifies that the station lies within the selected element.
- If not, Steps 2–3 are repeated with a larger $k$ value.

### Step 4: PE Assignment 
Once the containing element is identified, the script determines which PE the station belongs to.

The assignment is based on three cases: 

 * **Case 1:** The station lies exactly on a node (within a small threshold ($10^{-5}$)).
   * The station is assigned to the same PE as that node.
 * **Case 2:** The station lies within an element whose nodes all belong to the same PE.
   * The station is assigned to that PE.
 * **Case 3:** The station lies within an element whose nodes belong to different PEs.
   * The script finds the nearest node and assigns the station to that node's PE. 
Node-to-PE assignments are determined using `partmesh.txt`.

<img width="600" height="300" alt="image" src="https://github.com/user-attachments/assets/572c19b4-d8cd-4ace-b6ca-6c03010478b9" />

*Figure 2. Illustration of the three PE assignment cases described in Step 4.*

### Step 5: Write Outputs
- Writes a summary file: `pe_output.csv`.
- Generates updated `fort.26` files for each PE containing at least one station by injecting formatted `POINTS` and `SPECOUT` lines.
- Preserves the original configuration of the input `fort.26` files. 

---

## Software Requirements
- **Python 3.x** (Standard Library)
- No external dependencies are strictly required (uses `collections`, `dataclasses`, `heapq`, and `csv`).

---


## Contact

For questions or modifications, please contact:

**Nicole Arrigo** \
North Carolina State University - Coastal & Computational Hydraulics Team \
Email: nkarrigo@ncsu.edu
