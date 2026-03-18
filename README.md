# Spatial-Temporal-Controls
SWAN+ADCIRC supplementary scripts and example of spatial and temporal controls. 

## Temporal Controls 

This control has been added to give flexibility to the user to simulate SWAN for a **unique timeframe** within the ADCIRC simulation.

There are two variations that need to be made to use the temporal controls.
1. On the ADCIRC input side - the namelist SWANTimeControl must be used and the RunStartDateTime must be set with the start of the ADCIRC simulation at the end of the ADCIRC model control file (`fort.15`).

```bash
&SWANTimeControl RunStartDateTime='20180907.000000' /
```

2. On the SWAN input side - the COMPUTE time in the SWAN input file (`fort.26`) can be altered to the desired time range.
- For example, to run a simulation for 4 out of the 9 days ADCIRC is running, change the COMPUTE time from 20180907.0000 to 20180912.0000.

```bash
TEST 1,0
COMPUTE 20180912.000000 1200 SEC 20180916.000000
STOP
```

This will result in SWAN running for four of the nine days that ADCIRC runs for, leading to faster wall clock run times of simulations.

## Spatial Controls 

This control has been added to give flexibility to the user to simulate SWAN for a **unique spatial domain** within the ADCIRC computational mesh.

The supplementary scripts are necessary to use the spatial controls and more detail is provided on each script. This workflow supports running SWAN over a selective spatial domain using internal source spectra to account for offshore swell enegery, with flexibility depending on whether the boundary spectra already exist or must be generated.

#### Workflow

<img width="404" height="412" alt="decision_tree" src="https://github.com/user-attachments/assets/3325b069-e0fa-4196-99bd-fc119b37b9f4" />

<img width="326" height="398" alt="cases" src="https://github.com/user-attachments/assets/d9db8fa4-d9e4-439e-90f4-653ceb96c6c7" />

## Contact

For questions or modifications, please contact:

**Nicole Arrigo**  \
North Carolina State University - Coastal & Computational Hydraulics Team  \
Email: nkarrigo@ncsu.edu

---
