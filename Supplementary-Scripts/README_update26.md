# update26.py - ADCIRC Spectral Output & PE Station Mapping

**Author:** Nicole Arrigo \
**Last Updated:** March 11, 2026 

---

## Overview
This script identifies which ADCIRC mesh element and Processing Element (PE) partition owns specific observation stations based on their longitude/latitude. It automates the creation of localized `fort.26` files for parallel partitions, ensuring that each processor only tracks the stations physically located within its sub-domain.

---

## Intended Use Cases
Use this script when:
- Mapping a list of global station coordinates to specific ADCIRC parallel partitions.
- Generating partition-specific `fort.26` files before high-performance computing runs.
- Handling nodes near partition boundaries where a station might technically sit between multiple PEs.
- Standardizing spectral output formatting across large-scale mesh datasets.

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

### Step 1: Read Mesh Files
- Reads through `fort.14` to load node coordinates and create element-to-nodes connections.
- Creates a reverse-lookup dictionary of elements touching each node.
- Reads `partmesh.txt` to determine which PE each node belongs to.

### Step 2: Spatial Search
For each station:
- It identifies the $k$ nearest nodes using a priority queue (`heapq`).
- If a station is within a very small threshold ($10^{-5}$) of a node, it is assigned directly to that node's PE, skipping over logic in Step 3. 
- If not, the search radius ($k$) and tolerance ($\epsilon$) expand dynamically until an enclosing element is found.

### Step 3: PE Assignment 
- The script identifies the three nodes forming the enclosing element.
- It checks the PE assignment for each node via `partmesh.txt`.
- If all three nodes have matching PE, then assign to that PE.
- If the nodes belong to different PEs, when stationss mear partition boundaries creating ghost node/edge case, the station is assigned to the PE that owns the majority of the element's nodes.
  


### Step 4: Write Outputs
- Writes the `pe_output.csv` summary.
- Generates formatted `fort.26` files for each PE that contains at least one station by injecting formatted `POINTS` and `SPECOUT` lines while preserving the configuration from `fort.26` file used as an input. 

---

## Validation Test Case
A test case was created using 425 observation stations distributed throughout the EC95 mesh to ensure success across many elements and PE partitions.

<img width="975" height="567" alt="image" src="https://github.com/user-attachments/assets/ec032387-7972-469a-ac0a-32f33439d9b4" />

*Figure 1. Decomposition of the EC95 ADCIRC mesh across 128 processor cores. Colored triangular elements indicate PE partitions, while black markers show the spatial distribution of the 425 observation stations used in the test case.*

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
