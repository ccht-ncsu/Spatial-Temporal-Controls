## Overview 

- update13.py - to specify desired spatial domain and internal source spectra locations
  - Produces updated `fort.13`
- export_spec26.py - to output wave spectra (useful regardless of using spatial controls, beneficial for outputting spectral files efficiently for any purpose)
  - Produces updated local `fort.26` files
- apply_spec26.py - to be used with a modified fort.13 (using the SWAN Local Control nodal attribute) to input spectral boundary conditions
  - Produces updated local `fort.26` files 

#### Workflow for Spatial Controls 

There isn't one single workflow when using the spatail controls. The steps are dependent on the source of input spectra as displayed below.  

<img width="326" height="398" alt="cases" src="https://github.com/user-attachments/assets/d9db8fa4-d9e4-439e-90f4-653ceb96c6c7" />

---
