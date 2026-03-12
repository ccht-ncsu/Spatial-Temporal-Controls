# source_prep.py
#
#
# Author: Nicole Arrigo 7.30.2025
# Unity ID: nkarrigo
# Purpose:  Create fort.26 files with internal source node boundary commands 
# for each PE folder. 
# 
# 
# INPUTS: directory location- fort.13, partmesh.txt, fort.26 
#
# Full Procedure Summary:
#           --Create a GeoDataFrame from a SWAN+ADCIRC mesh net CDF file,
#           that can be later input into ArcGIS Pro.
#           --Create polygons based on longitude and latitude lists
#           and convert these to shapefiles.
#           --Add the GeoDataFrame, polygon shapefiles, and a Hurricane Florence
#           best track shapefile into ArcGIS using arcpy mapping.
#           --Prompt the user to choose a polygon out of the three defualts
#           or to draw their own which will be used for the Fortran file
#           manipulation.
#           --Read the fort.14 mesh domain file, which contains SWAN+ADCIRC's
#           mesh domain (x and y coordinates, and node numbers). Iterate through
#           the list of nodes and determine which nodes lie within the selceted
#           polygon and which nodes do not.
#           --Read the fort.13 file, which contains nodal attributes for each
#           node in the mesh. Write a new fort.13 file with a new nodal attribute
#           for SWAN_on or off based on which nodes are within the selected polygon.
#           --Once the file is saved, create a map with the mesh GeoDataFrame,
#           best track of Hurricane Florence, and the selected polygon.
#           --Report the success of the process with the map png image to a HTML report.
#
#
# Main Steps:
# Step 1: Create a dictionary based on internal source nodes from fort.13 and store side number.
#
# Step 2: Using the partmesh.txt file, add each internal source nodes PE folder to the dictionary.
#
# Step 3: Group internal source nodes by PE folder.
#
# Step 4: Generate lines Boundspec lines based on node and side number. 
#
# Step 5: Create fort.26 files for each PE folder with corresponding source lines. 
#
# Step 6: Copy the new fort.26 files to the corresponding PE folders. 
#
# Software Requirements: Python libraries os and collections must be installed.
#
#
# Usage: base_directory polygon_choice
#
# Example input: C:\Users\nicol\Documents\ArcGIS\Projects\swm_modernization poly1


# import libraries and packages
import os
from collections import defaultdict

#-----------------
# 



def extract_internal_sources(fort13_file, partmesh_file):
    internal_sources = {}

    # First: extract from fort.13
    with open(fort13_file, 'r') as f:
        lines = f.readlines()

    i = 0
    found = 0
    while i < len(lines):
        if lines[i].strip().lower() == "swan_local_control":
            found += 1
            num = int(lines[i+1].strip())
            i += 2

            if found == 1:
                i += num  # skip the first block
            elif found == 2:
                for _ in range(num):
                    parts = lines[i].strip().split()
                    if len(parts) >= 3 and parts[1] == '1':
                        node = int(parts[0])
                        side = int(parts[2])
                        internal_sources[node] = {"side": side}  # store as nested dict
                    i += 1
                break  # done after second block
        else:
            i += 1

    # Second: attach PE folder info from partmesh.txt
    with open(partmesh_file, 'r') as f:
        part_lines = f.readlines()

    for node in internal_sources:
        pe_number = int(part_lines[node - 1].strip())  # node N = line N
        internal_sources[node]["PE"] = pe_number -1

    return internal_sources


# 
sources = extract_internal_sources(
    r"fort.13",
    r"partmesh.txt"
)

print(sources)



# Group internal source nodes by PE Folder
pe_nodes = defaultdict(list)
for node, data in sources.items():
    pe = data["PE"]
    side = data["side"]
    pe_nodes[pe].append((node, side))

# Loop through each pe value and generate its fort.26
for pe, nodes in pe_nodes.items():
    boundspec_lines = []

    for node, side in nodes:
        spec_filename = f"bnd{node}.spc"
        line = f"BOUndspec SIDE {side} CONstant FILE '{spec_filename}' 1\n"
        boundspec_lines.append(line)

    boundshape_line = "BOUnd SHAPespec JONswap 3.3 PEAK DSPR DEGRees\n"

    # Input/output file paths
    original_fort_26_file = r"fort.26"
    output_fort_26_file = fr"pe{pe}_fort.26"

    # Function to insert shape and spec lines
    def update_fort_26_in(existing_file, new_file, boundshape_line, boundspec_lines):
        with open(existing_file, 'r') as infile:
            lines = infile.readlines()

        num_index = None
        star_index = None

        for i, line in enumerate(lines):
            if 'NUM STOPC DABS=0.005 DREL=0.01 CURVAT=0.005 NPNTS=95 NONSTAT MXITNS=20' in line:
                num_index = i
            if '$*************************************************************' in line:
                star_index = i

        new_lines = lines[:num_index + 2]
        new_lines.append(boundshape_line)
        new_lines.append('$\n')
        new_lines.extend(boundspec_lines)
        new_lines.append('$\n')
        new_lines.extend(lines[star_index:])

        with open(new_file, 'w') as outfile:
            outfile.writelines(new_lines)

    # Create the file
    update_fort_26_in(original_fort_26_file, output_fort_26_file, boundshape_line, boundspec_lines)
    print(f"Created {output_fort_26_file} with {len(boundspec_lines)} BOUndspec entries.")




    # Format destination folder like PE002
    pe_folder = f"PE{pe:04d}"
    #os.makedirs(pe_folder, exist_ok=True)  # Create folder if it doesn't exist

    # Destination path
    destination_file = os.path.join(pe_folder, "fort.26")

    # Copy the generated file into the folder
    import shutil
    shutil.copy(output_fort_26_file, destination_file)

    print(f"Copied to {destination_file}")
