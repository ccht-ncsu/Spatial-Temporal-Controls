## Overview 

- make13.py - to specify desired spatial domain and internal source spectra locations
- update26.py - to output wave spectra (useful regardless of using spatial controls, beneficial for outputting spectral files efficiently for any purpose)
- source_prep.py - to be used with a modified fort.13 (using the SWAN Local Control nodal attribute) to input spectral boundary conditions 

#### Workflow for Spatial Controls 

- Step 1 - make13.py 
- Step 2 - update26.py (only if obtaining spectra from a full domain simulation)
- Step 3 - source_prep.py 

---
