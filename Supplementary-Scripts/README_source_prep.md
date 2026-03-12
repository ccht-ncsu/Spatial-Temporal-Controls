# source_prep.py - SWAN Spectral Input Command Generator 

**Author:** Nicole Arrigo  \
**Last Updated:** March 12, 2026

---

## Overview
This script identifies and assigns *selective SWAN local control regions* and *internal source nodes* within an ADCIRC `fort.14` mesh using a user-defined polygon. It produces an updated `fort.13` file containing a new nodal attribute (`swan_local_control`) and a CSV summarizing the internal source node information.


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
- `fort.13` – ADCIRC nodal attributes file containing the `swan_local_control` attribute
- `fort.26` – SWAN input file to be used as template for inserting boundary condition commands
- `partmesh.txt` - ADCIRC partition file mapping nodes to subdomains
---

## Outputs

- **Updated `fort.26` Files**
  - For each subdomain partition (PE folder), the script generates a customized `fort.26` file containing the appropriate internal source boundary commands for the nodes assigned to the specific partition:
BOUndspec SIDE <side> CONstant FILE 'bnd<node>.spc' 1
BOUnd SHAPespec JONswap 3.3 PEAK DSPR DEGRees

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

## Software Requirements

The following Python libraries are required:

- `os`
- `collections`
- `shutil`

These libraries are included in the *standard Python library* and do not require additional installation.
---

## Contact

For questions or modifications, please contact:

**Nicole Arrigo**  \
North Carolina State University - Coastal & Computational Hydraulics Team  \
Email: nkarrigo@ncsu.edu

---
