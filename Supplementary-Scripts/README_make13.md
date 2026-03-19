# make13.py - SWAN Local Control & Internal Source Node Identification

**Author:** Nicole Arrigo  \
**Last Updated:** March, 2026

---

## Overview
To use the SWAN spatial controls, this script is necessary to identify and assign a *selective region of the mesh to run SWAN*. When running a nearshore SWAN simulation, spectral 'boundary' inputs can account for offshore generated swell wave energy and will help to preserve the accuracy of a partial domain simulation. These spectra can come from another wave model, wave buoy data, or a previous ADCIRC+SWAN full domain simulation.  

This script takes a user-defined polygon, representing the region where SWAN should be active, and also identifies *internal source nodes* (as locations to apply spectral boundary conditions) on the boundaries of that polygon (either in user-provided locations or at every boundary node). It produces an updated nodal attribute file (`fort.13`) containing a new attribute (`swan_local_control`) identifying active and inactive nodes and nodes to apply spectral sources and a CSV summarizing this internal source node information.

---

## Intended Use Cases

- Running SWAN on a *partial domain* of a larger ADCIRC mesh. This script will add a new nodal attribute to a `fort.13` file to indicate which vertices should be included in the computations. It can also do one or both of the following optional tasks:
   - Applying **input boundary spectra** only along selected internal sources. If the user has wave spectra (either from another SWAN simulation, or from a buoy), then this script will find the nearest ADCIRC mesh vertices and mark them as sources where those spectra will be applied during the simulation.
   - Generating internal source locations for **partial domain SWAN simulations**. If the user wants to output wave spectra along the edge of the active region (e.g. to use as sources in a follow-on simulation), then this script will identify the ADCIRC mesh vertices along that edge and write files that can be used to control the output of wave spectra (by using the `update26.py` script in this repository).

---

## Expected Results 

The following image displays what a modified `fort.13` file would include for `swan_local_control`. 

<img width="1716" height="600" alt="Untitled (5 72 x 2 in) (1)" src="https://github.com/user-attachments/assets/beaeb4a4-6765-4a65-b489-d7dd9b2b31a6" />

*Figure 1. Active SWAN nodes within the EC95 ADCIRC mesh based on user-specified polygon. Green elements correspond to areas of the mesh where SWAN is activated and red dots represent nodes where internal source spectra are applied as 'boundary conditions' for the partial domain.*


---

The workflow supports **two operational modes** for defining internal source nodes:

1. **Boundary node based (no CSV provided):** Internal source nodes are identified based on the boundaries of the partial domain. These locations are summarized in a CSV and this would be used in a full domain simulation to output spectra at these locations (using update26.py). 
2. **Station-based (CSV provided):** Internal source node locations are selected by user, specifying station locations (lon/lat) and finding the nearest mesh nodes to each station. This would be the case when input spectra already exist from a buoy or another wave model simulation.

This enables flexible SWAN simulations, allowing for the **SWAN Local Control (SLC)** attribute to enable partial-domain SWAN runs and interior boundry conditions (internal sources).


---

## Inputs

### Required Files
- `fort.14` – ADCIRC mesh file
- `fort.13` – ADCIRC nodal attributes file

### Optional Files
- **Station CSV** (optional): Used to define internal source nodes explicitly

  Expected format:
  ```csv
  Station,Longitude,Latitude
  ST01,-78.5432,34.1234
  ST02,-78.6123,34.0876
  ```

### Hardcoded Inputs
- Polygon vertices (longitude/latitude) defining the region of interest
- CSV file name if one is provided (otherwise None)
---

## Outputs

- **Updated `fort.13`**
  - Adds a new nodal attribute: `swan_local_control`
  - Includes non default value nodes (off or internal source nodes)
  - Nodes are "on" or "off" based on polygon
  - Nodes are internal sources depending on if csv is given. If not, they are determined by neighbor method

- **Internal Source CSV**
  - Node IDs used as internal SWAN sources
  - Associated station names and coordinates
  - This can be used with the update26.py code for cases of exporting spectra

---

## Methodology

The following steps demonstrate how the script works internally. To run the script, the user only needs to define the polygon vertices of the region of interest and specify whether internal sources are existing or need to be generated. 

### Step 1: User Inputs
- Read required files and user-defined parameters
- Detect whether a station CSV is provided

### Step 2: Polygon Creation
- Define polygon in lon/lat
- Convert to shapely geometry (optionally exported as a shapefile)

### Step 3: Mesh Parsing
- Read nodes and elements from `fort.14`
- Identify boundary segments and neighboring node relationships

### Step 4: Polygon Containment Test
- Determine which nodes fall inside the polygon
- Separate nodes inside vs. outside the region of interest

### Step 5: Internal Source Node Identification

#### Case 1: No CSV Provided (Geometry-Based)
- Internal source nodes are defined as:
  - Nodes **inside** the polygon
  - That share at least one element neighbor **outside** the polygon

This approach is typically used when:
- Running a **full-domain SWAN simulation**
- Exporting internal source spectra for use in a **partial-domain SWAN model**

#### Case 2: CSV Provided (Station-Based)
- Each station location (lon/lat) is snapped to the nearest mesh node
- Nearest-node selection uses squared-distance minimization in lon/lat space
- Node order follows the CSV order

This approach is typically used when:
- Boundary spectra already exist
- Stations are intended to act as **internal SWAN forcing points** in an partial simulation

### Step 6: Write Updated `fort.13`
- Append the `swan_local_control` nodal attribute
- Preserve existing nodal attributes and formatting

### Step 7: Write Output CSV
- Save internal source node IDs and locations

---

## Software Requirements

The following Python packages are required:

- `numpy`
- `matplotlib`
- `netCDF4`
- `shapely`
- `geopandas`

---

## Contact

For questions or modifications, please contact:

**Nicole Arrigo**  \
North Carolina State University - Coastal & Computational Hydraulics Team  \
Email: nkarrigo@ncsu.edu

---
