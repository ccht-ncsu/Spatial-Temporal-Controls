# Hurricane Florence (2018) Simulation using Varying Spatial and Temporal SWAN Domains

**Author:** Nicole Arrigo  \
**Last Updated:** March 2026

---

## Overview

The objective of this example is to demonstrate how to run **SWAN+ADCIRC simulations using the EC95 mesh** for **Hurricane Florence (2018)** to explore different spatial and temporal modeling configurations.

This example illustrates how the same model setup can be adapted to run:

- Case 1 - Full SWAN spatial and temportal domain simulations
- Case 2 - Partial time simulations 
- Case 3 - Partial spatial domain simulations using SWAN Local Control (SLC)
- Case 4 - Combined partial domain and partial time simulations

These workflows can be used to **reduce computational cost** while maintaining accurate wave predictions in coastal regions.

---

## Intended Use Cases

- Simulating waves nearshore on a *partial domain* of a larger ADCIRC mesh
- Outputting wave spectra and applying these as **internal source spectra** along a partial domain
- Simulating waves for a portion of the time that circulation is simulated 

---
## Files Included

This example includes the following input files:

- `fort.14` – ADCIRC mesh file (EC95 mesh)
- `fort.13` – ADCIRC nodal attributes file
- `fort.15` – ADCIRC model control file
- `fort.22` – Hurricane wind and pressure forcing file
- `fort.26` – SWAN model control file
- `swaninit` – SWAN initialization file

These files provide a complete base configuration for running **SWAN+ADCIRC simulations of Hurricane Florence (2018)**.

---
The workflow supports **two operational modes** for defining internal source nodes:

1. **Geometry-based (no CSV provided):** Internal source nodes are identified using neighboring nodes of partial domain.
2. **Station-based (CSV provided):** Internal source nodes are selected by user, specifying station locations (lon/lat) and finding the nearest mesh nodes to each station.

This enables flexible SWAN simulations, allowing for the **SWAN Local Control (SLC)** attribute to enable partial-domain SWAN runs and interior boundry conditions (internal sources).

---

Compile or load the SWAN+ADCIRC executable as appropriate for your system.

---

## Case 1: Full Domain Simulation

The default configuration represents a **full domain, full time simulation**.

In this configuration:

- SWAN runs over the **entire ADCIRC mesh**
- The simulation covers the **entire storm duration**

Run the model using the SWAN+ADCIRC executable:
```bash
padcswan
---

## Case 2: Full Domain Simulation

The default configuration represents a **full domain, full time simulation**.

In this configuration:

- SWAN runs over the **entire ADCIRC mesh**
- The simulation covers the **entire storm duration**

Run the model using the SWAN+ADCIRC executable:
```bash
padcswan

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

---

## Discussion

---

## Contact

For questions or modifications, please contact:

**Nicole Arrigo**  \
North Carolina State University - Coastal & Computational Hydraulics Team  \
Email: nkarrigo@ncsu.edu

---
