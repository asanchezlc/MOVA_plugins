

import os
import helpers.outils as outils

"""
File Duties:

Obtains the geometry from a DXF file and writes it to a text file (to be read
by MOVA).

Requires in CAD file:
    - Format: .dxf
    - Channels:
        -> be defined in one of the following layers:
            'x_pos', 'x_neg', 'y_pos', 'y_neg', 'z_pos', 'z_neg'
        -> be defined as text entities, being the point of the definition of the
            text the position of the sensor [IMPORTANT: select the text and place it
            exactly in the end of a line]
        -> be numbered from 1 to N, where N is the number of sensors

Remarks:
    - See "Geometry_AutoCAD.dxf" for an example.     

Future Improvements:
    - Use groups in AutoCAD (or other approaches) to deal with multi-setup; in fact, write_geometry_txt
        is prepared to be inside a loop, which one setup processed at a time.
"""
#####################################
# MODIFIABLE PARAMETERS
#####################################
dxf_file = 'Geometry_AutoCAD.dxf'                  # DXF file to be read
path = os.path.join('src', 'examples')             # DXF file path
output_file = dxf_file.replace('.dxf', '.txt')     # Output file name
output_file_path = os.path.join(path, output_file) # Output file path
#####################################

#####################################
# CODE
#####################################
dxf_file_path = os.path.join(path, dxf_file)
all_points_coord, all_elements_coord_connect = outils.read_nodes_lines(
    dxf_file_path)
sensors_key = outils.read_text_vectors(dxf_file_path, all_points_coord)
outils.write_geometry_txt_2(output_file_path, all_points_coord, all_elements_coord_connect, sensors_key)
