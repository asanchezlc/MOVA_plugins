import helpers.outils as outils
import helpers.sap2000 as sap2000

import os

"""
File Duties:

Obtains the geometry from a SAP2000 file and writes it to a text file (to be read
by MOVA).

Requires in SAP2000 file:
    - Format: .sdb
    - Channels: are defined as joint forces as follows:
        -> are defined in one of the following load patterns:
            'References', 'Setup_1', 'Setup_2', ..., 'Setup_N'
        -> The value of the force is the number of the channel
        (by default, the force is in kN; switch force_in_kN to False
        to read it in N)
        -> IMPORTANT: if there are no multisetups, define forces only in the
            'References' load pattern,

Remarks:
    - See "Geometry_MultiSetup.sdb" for an example.
"""

#####################################
# MODIFIABLE PARAMETERS
#####################################
sbd_file = 'Geometry_MultiSetup.sdb'
path = os.path.join('src', 'examples')
FilePath = os.path.join(path, sbd_file)
force_in_kN = True
#####################################

#####################################
# CODE
#####################################
# 1. Open SAP2000 file
mySapObject = sap2000.app_start()
SapModel = sap2000.open_file(mySapObject, FilePath)
sap2000.unlock_model(SapModel)

# 2. Read geometry
round_coordinates = True
all_points = sap2000.get_point_obj_names(SapModel)
all_points_coord = sap2000.get_pointcoordinates(
    all_points, SapModel, round_coordinates=round_coordinates)

all_elements = sap2000.get_frame_obj_names(SapModel)
all_elements_coord_connect = sap2000.get_frameconnectivity(all_points, all_elements,
                                                           SapModel, all_points_coord=all_points_coord)

# 3. Read channels
sensors = dict()

# A) References
load_pattern = "References"
forces_setup = sap2000.get_point_forces(
    'ALL', SapModel, load_pattern=load_pattern,
    return_kN=force_in_kN)
acc_channels = outils.get_accelerometer_channels_from_forces(
    forces_setup)
sensors['References'] = [data for key, data in acc_channels.items()]

# B) Setups
run_loop, i = True, 1
base_load_pattern = 'Setup_'
while run_loop:
    load_pattern = f'{base_load_pattern}{i}'
    forces_setup = sap2000.get_point_forces(
        'ALL', SapModel, load_pattern=load_pattern,
        return_kN=force_in_kN)
    acc_channels = outils.get_accelerometer_channels_from_forces(
        forces_setup)
    if len(acc_channels) > 0:
        i += 1
        sensors[load_pattern] = [data for key, data in acc_channels.items()]
    else:
        run_loop = False
n_setups = i - 1

# 4. Write geometry in txt file
sensors_key = list()
for data in sensors['References']:
    sensors_key.append({data['point']: data['dir']})

# A) No setups
if n_setups == 0:
    output_file_path = os.path.join(
        path, sbd_file.replace('.sdb', f'.txt'))
    outils.write_geometry_txt_2(
        output_file_path, all_points_coord, all_elements_coord_connect, sensors_key)
# B) With setups
else:
    for setup in range(1, n_setups + 1):
        sensors_setup = list()
        for data in sensors[f'{base_load_pattern}{setup}']:
            sensors_setup.append({data['point']: data['dir']})
        output_file_path = os.path.join(
            path, sbd_file.replace('.sdb', f'_setup_{setup}.txt'))
        outils.write_geometry_txt_2(
            output_file_path, all_points_coord, all_elements_coord_connect, sensors_key + sensors_setup)
