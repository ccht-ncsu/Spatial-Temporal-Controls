# Spatial-Temporal-Controls
SWAN+ADCIRC supplementary scripts and example of spatial and temporal controls. 
With these controls, the user can specify exactly when and where SWAN will perform its computations during a coupled ADCIRC+SWAN simulation. 
Instead of having to run SWAN on the full mesh and for the entire timeframe, the user can limit SWAN to a spatial region near landfall and a temporal duration at the height of the storm. 
These controls have the potential to speed-up the overall simulation, without much sacrifice in accuracy.

## Temporal Controls 

This control has been added to give flexibility to the user to simulate SWAN for a **unique timeframe** within the ADCIRC+SWAN simulation. 
Previously, it was required that SWAN would compute for the entire timeframe of the simulation, which was inefficient if the storm was far offshore and the waves were small. 
Now, the user can control SWAN to compute only for a portion of the simulation, thus allowing for an efficiency gain when SWAN is idle.

There are two changes that need to be made to use the temporal controls.
1. On the ADCIRC input side - the namelist `SWANTimeControl' must be used and the `RunStartDateTime' must be set with the start of the current ADCIRC simulation at the end of the ADCIRC model control file (`fort.15`).

```bash
&SWANTimeControl RunStartDateTime='20180907.000000' /
```

2. On the SWAN input side - the `COMPUTE' time in the SWAN input file (`fort.26`) can be altered to the desired time range.
- For example, to run a simulation for only four days, change the COMPUTE time.

```bash
TEST 1,0
COMPUTE 20180912.000000 1200 SEC 20180916.000000
STOP
```

This will result in SWAN running for four days, regardless of the ADCIRC timeframe, thus leading to faster wall clock run times of simulations.

## Spatial Controls 

This control has been added to give flexibility to the user to simulate SWAN for a **unique spatial domain** within the ADCIRC computational mesh. 
Previously, it was required that SWAN would compute on the full ADCIRC mesh, which again was inefficient in regions far from the storm. 
Now, the user can specify a region for the SWAN computations, such as a portion of the coastal ocean near landfall, thus allowing for an efficency gain in the regions where SWAN is idle.

The supplementary scripts are necessary to use the spatial controls, and more detail is provided on each script. This workflow supports running SWAN over a selective spatial domain using internal source spectra to account for offshore swell enegery, with flexibility depending on whether the boundary spectra already exist or must be generated.

#### Workflow

<img width="404" height="412" alt="decision_tree" src="https://github.com/user-attachments/assets/3325b069-e0fa-4196-99bd-fc119b37b9f4" />

<img width="326" height="398" alt="cases" src="https://github.com/user-attachments/assets/d9db8fa4-d9e4-439e-90f4-653ceb96c6c7" />

## Contact

For questions or modifications, please contact:

**Nicole Arrigo**  \
North Carolina State University - Coastal & Computational Hydraulics Team  \
Email: nkarrigo@ncsu.edu

---
