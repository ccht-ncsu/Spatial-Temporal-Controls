# make13.py - SWAN Local Control & Internal Source Node Identification

**Author:** Nicole Arrigo  \
**Last Updated:** January 20, 2026

---

## Overview
This script identifies and assigns *selective regions of the mesh to run SWAN* and *internal source nodes* (as locations to apply spectral boundary conditions) using a user-defined polygon. It produces an updated nodal attribute file (`fort.13`) containing a new attribute (`swan_local_control`) identifying active and inactive nodes and nodes to apply spectral sources at and a CSV summarizing this internal source node information.


---

## Intended Use Cases

- Running SWAN on a *partial domain* of a larger ADCIRC mesh
- Applying **input boundary spectra** only along selected internal sources
- Generating internal source locations for **SLC-based SWAN simulations**

---

The workflow supports **two operational modes** for defining internal source nodes:

1. **Geometry-based (no CSV provided):** Internal source nodes are identified using neighboring nodes of partial domain.
2. **Station-based (CSV provided):** Internal source nodes are selected by user, specifying station locations (lon/lat) and finding the nearest mesh nodes to each station.

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
  - This can be used with the make26.py code for cases of exporting spectra

---

## Methodology

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
- Stations are intended to act as **internal SWAN forcing points** in an SLC simulation

### Step 6: Write Updated `fort.13`
- Append the `swan_local_control` nodal attribute
- Preserve existing nodal attributes and formatting

### Step 7: Write Output CSV
- Save internal source node IDs and associated metadata

---

## Expected Results 

The following image displays what a modified `fort.13` file would include for `swan_local_control`. 

<img width="975" height="567" alt="image" src="https://github.com/user-attachments/assets/ec032387-7972-469a-ac0a-32f33439d9b4" />

*Figure 1. Active SWAN nodes within the EC95 ADCIRC mesh based on user-specified polygon. Green Colored triangular elements indicate PE partitions, while black markers show the spatial distribution of the 425 observation stations used in the test case.*


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
