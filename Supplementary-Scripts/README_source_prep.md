# source_prep.py - SWAN Spectral Input Command Generator 

**Author:** Nicole Arrigo  \
**Last Updated:** March 12, 2026

---

## Overview
This script prepares *SWAN internal source boundary commands* for parallel SWAN+ADCIRC simulations. It reads internal source node information from the ADCIRC nodal attribute file (`fort.13`) and assigns each source node to its corresponding *subdomain partition (PE folder)* after domain decomposition has been run using the `partmesh.txt` file.

For each subdomain folder, the script generates a *local SWAN input file (`fort.26`)* containing the required `BOUndspec` commands that specify spectral forcing. The script then copies the generated files into the corresponding subdomain directories.

This automates the preparation of *local SWAN input files* when running parallel simulations with internal source spectra.

---

## Intended Use Cases

- Running SWAN on a *partial domain* of a larger ADCIRC mesh
- Applying **input boundary spectra** only along selected internal sources

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
 
```bash
BOUnd SHAPespec JONswap 3.3 PEAK DSPR DEGRees
BOUndspec SIDE <side> CONstant FILE 'bnd<node>.spc' 1
```
---

## Methodology


### Step 1: Extract Internal Source Nodes
- Reads the `swan_local_control` attribute from the `fort.13` file and identifies nodes marked as internal sources.

For each source node, the script extracts and stores:
- Node ID
- Boundary side number

### Step 2: Assign Nodes Subdomain Folders
- Using `partmesh.txt`, each internal source node is mapped to its corresponding subdomain (PE folder) and stored.

### Step 3: Group Nodes by Subdomain Folder
- Internal source nodes are grouped according to their assigned subdmain folder.
- This ensures each partition contains only the nodes belonging to it.


### Step 4: Generate Boundary Commands
- For each internal source node, the script generates a SWAN boundary command using the side numbers previously stored:
```bash
BOUndspec SIDE <side> CONstant FILE 'bnd<node>.spc' 1
```
- Each node references a spectral file named:
```bash
bnd<node>.spc
```

### Step 5: Create `fort.26` files 
- For each PE folder, a new SWAN input file (`fort.26`) is created with following information inserted:

1. Spectral shape definition
2. Internal source boundary commands for all nodes within partition
3. The original content from the SWAN input file

- This preserves the structure of the original `fort.26` file while adding the required boundary inputs.

### Step 6: Distribute Files to Subdomain Folders
- Each generated `fort.26` file is copied into its corresponding subdomain directory:
```bash
PE####/fort.26
```
- This ensures each partition runs with the SWAN boundary commands corresponding to *only the internal sources located on each partition*.

---

## Software Requirements

The following Python libraries are required:

- `os`
- `collections`
- `shutil`

- These libraries are included in the *standard Python library* and do not require additional installation.
---

## Contact

For questions or modifications, please contact:

**Nicole Arrigo**  \
North Carolina State University - Coastal & Computational Hydraulics Team  \
Email: nkarrigo@ncsu.edu

---
