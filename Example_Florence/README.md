# Hurricane Florence (2018) using Varying Spatial and Temporal SWAN Domains

**Author:** Nicole Arrigo  \
**Last Updated:** March 2026

---

## Overview

The objective of this example is to demonstrate how to run **SWAN+ADCIRC simulations** using the EC95 mesh for Hurricane Florence (2018) to explore **different spatial and temporal modeling configurations**.

This example illustrates how the same model setup can be adapted to run:

- Case 1 - Full SWAN spatial and temporal domain simulations (default SWAN+ADCIRC configuration) 
- Case 2 - Partial time simulations 
- Case 3 - Partial spatial domain simulations 
- Case 4 - Combined partial spatial and temporal domain simulations

These workflows can be used to **reduce computational cost** while maintaining accurate wave predictions in coastal regions.

---

## Intended Use Cases

- Simulating waves for a portion of the time that circulation is simulated (Case 2 and Case 4)
- Simulating waves nearshore on a *partial domain* of a larger ADCIRC mesh (Case 3 and Case 4)
  - Outputting wave spectra and applying these as **internal source spectra** along a partial domain

---
## Files Included

#### Input Files
This example includes the following input files:

- `fort.14` – ADCIRC mesh file (EC95 mesh)
- `fort.13` – ADCIRC nodal attributes file
- `fort.15` – ADCIRC model control file (*Note that the final line of this file includes the new namelist needed for temporal controls*)
- `fort.22` – Hurricane wind and pressure forcing file
- `fort.26` – SWAN model control file
- `swaninit` – SWAN initialization file

These files provide a complete base configuration for running **SWAN+ADCIRC simulations of Hurricane Florence (2018)**.

#### Output Files
The following output files should be produced when running through the example:

- `modified_fort.13` - ADCIRC nodal attributes file with the new attribute SWAN Local Control to identify inactive nodes and internal source nodes (Case 3).
- `station_locations.csv` - list of internal source node locations where spectra should be exported.


---

Compile or load the SWAN+ADCIRC executable as appropriate for your system.

---

## Case 1: Full Domain Simulation - Default

The default configuration represents a **full domain, full time simulation**.

In this configuration:

- SWAN runs over the **entire ADCIRC mesh**
- The simulation covers the **entire storm duration**

Run the model as you usually would using the ADCIRC+SWAN executable `padcswan`

---

## Case 2: Partial Time Simulation

This configuration represents a **full spatial domain, partial time simulation**.

In this configuration:

- SWAN runs over the **entire ADCIRC mesh**
- The simulation covers a **specified timeframe** within the storm duration


This control has been added to give flexibility to the user to simulate SWAN for a **unique timeframe** within the ADCIRC simulation.

There are two variations that need to be made to use the temporal controls.
1. On the ADCIRC input side - the namelist SWANTimeControl must be used and the RunStartDateTime must be set with the start of the ADCIRC simulation at the end of the ADCIRC model control file (`fort.15`).

```bash
&SWANTimeControl RunStartDateTime='20180907.000000' /
```

2. On the SWAN input side - the COMPUTE time in the SWAN input file (`fort.26`) can be altered to the desired time range.
- To run this simulation for 4 out of the 9 days ADCIRC is running, change the COMPUTE time from 20180907.0000 to 20180912.0000.

```bash
TEST 1,0
COMPUTE 20180912.000000 1200 SEC 20180916.000000
STOP
```

This will result in SWAN running for four of the nine days that ADCIRC runs for, leading to faster wall clock run times of simulations.

---

## Case 3: Partial Spatial Domain Simulation

This configuration represents a **partial spatial domain, full time simulation**.

In this configuration:

- SWAN runs over a **specified spatial domain**
- Internal sources of wave spectra can be applied at SWAN domain boundaries to account for offshore swell energy
- The simulation runs SWAN and ADCIRC for one uniform timeframe 

This configuration enables efficient simulations focused on a **region of interest** while still accounting for offshore wave conditions.

This workflow supports **two approaches**, depending on whether internal source spectra already exist.

### Case 3a: Generate Internal Sources from a Full Domain Simulation

Use this approach if **no spectra currently exist**.
- Escpecially useful in engineering design when running repeated scenarios for design alternatives

#### Step 1: Define Partial Domain
- Run `make13.py` with a user-defined polygon of the region of interest 
- Outputs:
  - Modified `fort.13` with nodal attribute (`swan_local_control`) defining active nodes and internal source nodes
  - `station_locations.csv` containing internal source node locations (at every new 'boundary' node of partial domain)  

#### Step 2: Export Spectra from Full Domain Simulation
- Run a **full domain SWAN+ADCIRC simulation**
- Use `adcprep` as usual
- Use `station_locations.csv` with `update26.py` to:
  - Insert local commands into SWAN input file (`fort.26`) to **output spectra at internal source nodes**
- Upon running, this produces spectral files: bnd<xxxx>.spc

#### Step 3: Run Partial Domain Simulation
- Use the modified `fort.13` from Step 1  
- Include the generated spectral files (`bndXXXX.spc`)  
- Run `adcprep`  
- Run `source_prep.py` to:
  - Insert local boundary condiiton commands (`BOUndspec`) into each PE-specific `fort.26`  
- Run `padcswan`

### Case 3b: Use Predefined Internal Source Locations and Spectra 

Use this approach if **spectra already exist** (e.g., from another model, simulation, or observations).

#### Step 1: Define Internal Sources and Patial Domain
- Run `make13.py` with a user-defined polygon and internal_sources.csv with station locations (lon/lat). 
- Outputs:
  - Modified `fort.13` with nodal attribute (`swan_local_control`) defining active nodes and internal source nodes

#### Step 2: Run Partial Domain Simulation
- Use the modified `fort.13` from Step 1  
- Include spectral files to be used as input sources (`bndXXXX.spc`)  
- Run `adcprep`  
- Run `source_prep.py` to:
  - Insert local boundary condiiton commands (`BOUndspec`) into each PE-specific `fort.26`  
- Run `padcswan`

Both simulations will result in a partial spatial domain with spectral boundary forcings to account for offshore swell. 

---

## Case 4: Combined Partial Spatial and Temporal Simulation

This configuration combines both opitmizations and represents a **partial spatial domain, reduced time simulation**.

To run this configuration:
- Define the SWAN compute time in the SWAN input file (`fort.26`)
- Use make13.py with the desired spatial region and intrnal source settings (following the steps to obtain source spectra from a full domain simulation, if needed).
- With the modified nodal attribute file (`fort.13`), input spectra, and timing updated SWAN input file (`fort.26`), run ADCPREP to decompose the mesh.
- Next, run source_prep.py to ditribute the boundary spectra commands locally.
- Run `padcswan` for the partial spatial and temporal SWAN domain.   


---

## Expected Results


<img width="1716" height="600" alt="Untitled (5 72 x 2 in)" src="https://github.com/user-attachments/assets/92b1a9b5-0b26-428d-a90e-14ff33b8305e" />
*Figure 1. Significant wave heights for three varying spatial domains as Hurricane Florence is making landfall.*

This example demonstrates a 37% speedup between the full and partial simulations. 

---

## Discussion
This example demonstrates the flexibility of SWAN+ADCIRC simulations and how they can now be configured to balance accuracy and computational efficiency.

Key advantages of the workflows shown here include:
- Reducing model runtime
- Allowing targeted wave simulations in regions of interest
- Enabling reuse of spectra from larger simulations

---

## Contact

For questions or modifications, please contact:

**Nicole Arrigo**  \
North Carolina State University - Coastal & Computational Hydraulics Team  \
Email: nkarrigo@ncsu.edu

---
