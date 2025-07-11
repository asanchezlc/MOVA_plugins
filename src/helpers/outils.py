

import ezdxf

import matplotlib.pyplot as plt
import numpy as np
import os
import copy


def from_list_to_dof(list):
    if list[0] == 1:
        return 'U1'
    elif list[0] == -1:
        return '-U1'
    if list[1] == 1:
        return 'U2'
    elif list[1] == -1:
        return '-U2'
    if list[2] == 1:
        return 'U3'
    elif list[2] == -1:
        return '-U3'


def read_nodes_lines(dxf_file_path):
    """
    Function Duties:
        Retrieves all the lines in an AutoCAD dxf file.

    Input:
        .dxf file

    Output:
        points_dict: dict, with all the start and ending points of the lines in the dxf file
            e.g. points_dict = {'1': {'x': 0.0, 'y': 0.0, 'z': 0.0}, ...}
        lines_dict: dict, with all the lines in the dxf file
            e.g. lines_dict = {'1': {'Point_0': {'PointName': '1', 'x': 0.0, 'y': 0.0, 'z': 0.0},
                                    'Point_f': {'PointName': '2', 'x': 1.0, 'y': 1.0, 'z': 1.0}}}
    """
    doc = ezdxf.readfile(dxf_file_path)
    msp = doc.modelspace()

    points_dict, lines_dict = dict(), dict()
    unique_points = dict()
    point_counter, line_counter = 1, 1

    for line in msp.query("LINE"):
        start = point_key(line.dxf.start)
        end = point_key(line.dxf.end)

        # Get unique points
        for pt in [start, end]:
            if pt not in unique_points:
                unique_points[pt] = str(point_counter)
                points_dict[str(point_counter)] = {
                    'x': pt[0], 'y': pt[1], 'z': pt[2]}
                point_counter += 1

        # Create line
        lines_dict[str(line_counter)] = {
            'Point_0': {
                'PointName': unique_points[start],
                'x': start[0], 'y': start[1], 'z': start[2]
            },
            'Point_f': {
                'PointName': unique_points[end],
                'x': end[0], 'y': end[1], 'z': end[2]
            }
        }
        line_counter += 1

    return points_dict, lines_dict


def check_channels(channels, expected_channels) -> None:
    """
    Function Duties:
        Checks if the provided channels match the expected channels.
    """
    channels = set(channels)
    expected_channels = set(expected_channels)
    missing = expected_channels - channels
    extra = channels - expected_channels

    if missing:
        raise ValueError(
            f"ERROR | Some channels are not defined as text - lacking channels: {sorted(missing)}")
    if extra:
        raise ValueError(
            f"ERROR | Unexpected channels as text: {sorted(extra)}")


def round_6_sign_digits(number):
    """
    Function duties:
        Rounds a float to 6 significant digits
    """
    formatted_number = "{:.6g}".format(number)
    rounded_number = float(formatted_number)

    return rounded_number



def get_accelerometer_channels_from_forces(forces_setup):
    """
    Function Duties:
        Processes nodal force data (e.g. from SAP2000) and builds a dictionary
        of accelerometer channels with their location and measurement direction.

    Input:
        forces_setup : dict
            Dictionary containing point force data:
            - 'PointObj' : list of node names
            - 'F1', 'F2', 'F3' : lists of force values in local axes 1, 2, 3

    Output:
        acc_channels : dict
            Dictionary with structure:
            {
                'Channel_1': {'point': 'NodeA', 'dir': [±1, 0, 0]},
                'Channel_2': {'point': 'NodeB', 'dir': [0, ±1, 0]},
                ...
            }
            - Direction vector is aligned with the nonzero force component.
            - Channel number is inferred from the absolute value of the force.
    Notes:
        - Each nonzero force component creates one channel.
        - The output is sorted by channel number for consistency.
    Remark:
        For fully coherence, this function might be enhanced to totally match
        the structure of get_SGs_positions_dictionary; for that, a new
        get_point_forces function to obtain forces_setup would be required
    """
    point_ids = forces_setup['PointObj']
    f1 = forces_setup['F1']
    f2 = forces_setup['F2']
    f3 = forces_setup['F3']
    n_items_f1 = len([i for i in range(len(f1)) if f1[i] != 0])
    n_items_f2 = len([i for i in range(len(f2)) if f2[i] != 0])
    n_items_f3 = len([i for i in range(len(f3)) if f3[i] != 0])
    n_items = n_items_f1 + n_items_f2 + n_items_f3

    acc_channels = dict()
    for i in range(len(point_ids)):

        if f1[i] != 0:
            direction = [0, 0, 0]
            direction[0] = int(np.sign(f1[i]))
            channel_id = int(abs(f1[i]))
            acc_channels[f'Channel_{channel_id}'] = {
                'point': point_ids[i],
                'dir': direction
            }
        if f2[i] != 0:
            direction = [0, 0, 0]
            direction[1] = int(np.sign(f2[i]))
            channel_id = int(abs(f2[i]))
            acc_channels[f'Channel_{channel_id}'] = {
                'point': point_ids[i],
                'dir': direction
            }
        if f3[i] != 0:
            direction = [0, 0, 0]
            direction[2] = int(np.sign(f3[i]))
            channel_id = int(abs(f3[i]))
            acc_channels[f'Channel_{channel_id}'] = {
                'point': point_ids[i],
                'dir': direction
            }

    sorted_items = sort_string_separated_by(list(acc_channels), separator='_')
    acc_channels = {key: acc_channels[key] for key in sorted_items}

    # Assign direction (i.e. U1, U2...)
    acc_channels = add_direction_to_acc_channels(acc_channels)

    return acc_channels



def add_direction_to_acc_channels(channels):
    """
    Function Duties:
    - Add the 'direction' of the accelerometers to the channels dictionary.
    Input:
        channels: a dictionary containing 'dir' key, which is like
        [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], or [0, 0, -1].
    Output:
        channels_with_direction: a copy of the input dictionary with an additional
        'direction' key for each channel, containing the direction as a str.
        e.g. if [-1, 0, 0] -> '-U1' -> , if [0, 1, 0] -> 'U2', etc.
    """
    channels_with_direction = copy.deepcopy(channels)
    for ch in list(channels_with_direction):
        dir_vec = channels_with_direction[ch]['dir']
        if dir_vec[0] == 1:
            channels_with_direction[ch]['direction'] = 'U1'
        elif dir_vec[1] == 1:
            channels_with_direction[ch]['direction'] = 'U2'
        elif dir_vec[2] == 1:
            channels_with_direction[ch]['direction'] = 'U3'
        elif dir_vec[0] == -1:
            channels_with_direction[ch]['direction'] = '-U1'
        elif dir_vec[1] == -1:
            channels_with_direction[ch]['direction'] = '-U2'
        elif dir_vec[2] == -1:
            channels_with_direction[ch]['direction'] = '-U3'

    return channels_with_direction


def sort_list_string(list_str):
    """
    Function duties:
        Convert a list of string-numbers, that can start by "~",
        into a sorted list.
    Example:
        list_str = ['6', '7', '~3', None, '~5', '~10']
        sorted_list = ['6', '7', '~3', '~5', '~10', None]
    """
    none_elements = len([i for i in list_str if i is None])
    list_str = [i for i in list_str if i is not None]
    if isinstance(list_str[0], float):
        sorted_list = sorted(list_str)
    else:
        regular_numbers = [s for s in list_str if not s.startswith('~')]
        tilde_numbers = [s for s in list_str if s.startswith('~')]
        regular_numbers = sorted(regular_numbers, key=lambda x: float(x))
        tilde_numbers = sorted(tilde_numbers, key=lambda x: float(x[1:]))
        sorted_list = regular_numbers + tilde_numbers

    sorted_list += [None]*none_elements

    return sorted_list


def sort_string_separated_by(str_list, separator='_'):
    """
    Function Duties:
        Sorts a string with numbers separated by a separator
        example: ['Element_1', 'Element_10', 'Element_2'] ->
            -> ['Element_1', 'Element_2', 'Element_10']
    Input:
        str_list: list of strings
        separator: character that separates numbers in the strings
    Output:
        str_sorted: sorted list of strings
    """
    str_sorted = sorted(str_list, key=lambda x: int(x.split(separator)[-1]))

    return str_sorted


def point_key(point):
    """
    Rounds point to avoid accuracy issues
    """
    return (round(point[0], 6), round(point[1], 6), round(point[2], 6))


def read_text_vectors(dxf_file_path, points_dict):
    """
    Function Duties:
        Obtain the channels in proper format for MOVA file

    Input:
        dxf_file_path: str, path to the DXF file
        points_dict: dict, dictionary with points coordinates, used to match text insert points

    Output:
        vector_dict: dict with all the channels as follows:
        vector_dict = {
            '5': [1.0, 0.0, 0.0],  # channel 1 in x_pos direction in point "5"
            '2': [0.0, -1.0, 0.0],  # channel 2 in y_neg direction in point "2"
            ...
        }
    """
    doc = ezdxf.readfile(dxf_file_path)
    msp = doc.modelspace()

    vector_dict = list()

    # Mapping layer -> direction
    layer_to_vector = {
        'x_pos': [1.0, 0.0, 0.0],
        'x_neg': [-1.0, 0.0, 0.0],
        'y_pos': [0.0, 1.0, 0.0],
        'y_neg': [0.0, -1.0, 0.0],
        'z_pos': [0.0, 0.0, 1.0],
        'z_neg': [0.0, 0.0, -1.0],
    }

    # Retrieve all texts in one of the layers of layer_to_vector
    texts = [t for t in msp.query('TEXT MTEXT')
             if t.dxf.layer in layer_to_vector]
    # a must for the "for" loop below
    texts = sorted(texts, key=lambda t: int(t.dxf.text.strip()))

    expected_channels = [str(i) for i in range(1, len(texts) + 1)]
    channels = [text.dxf.text.strip() for text in texts]
    check_channels(channels, expected_channels)

    for text in texts:
        text_value = text.dxf.text.strip()
        layer_name = text.dxf.layer.strip().lower()

        insert_point = (
            round(text.dxf.insert[0], 6),
            round(text.dxf.insert[1], 6),
            round(text.dxf.insert[2], 6)
        )

        # Search coordinates in points_dict
        matched_point = None
        for point_id, coords in points_dict.items():
            if (
                round(coords['x'], 6) == insert_point[0] and
                round(coords['y'], 6) == insert_point[1] and
                round(coords['z'], 6) == insert_point[2]
            ):
                matched_point = point_id
                break

        if matched_point:
            vector_dict.append({point_id: layer_to_vector[layer_name]}) 
        else:
            raise ValueError(
                f"Insert point {insert_point} for text '{text_value}' not found in points_dict."
            )

    return vector_dict


def write_geometry_txt_2(FilePath, all_points_coord, all_elements_coord_connect, sensors) -> None:
    """
    Function Duties:
        Writes the geometry of the model to be read by ARTeMIS or another OMA software
    Input:
        FilePath: path to the file to be written
        all_points_coord: dictionary with all points coordinates
        all_elements_coord_connect: dictionary with all elements and their connections
        sensors: list of dictionaries, each one being {'point':dir} where:
            - the list contains the channels numbered from 1 to N
            - dir is a list with the direction of the channel, e.g. [1, 0, 0] or [0, 0, -1], ...
    """
    with open(FilePath, 'w') as file:
        file.write('\n')
        file.write('\n')
        file.write('GEOMETRY DEFINITION\n')
        file.write('\n')
        file.write('\n')

        # Part 1: Write NODES
        file.write('NODES ID, X, Y, Z\n')
        file.write('\n')
        # file.write(str(len(all_points_coord)) + '\n')
        for i in all_points_coord:
            if i is None:
                continue
            file.write(
                f"{i} {all_points_coord[i]['x']} {all_points_coord[i]['y']} {all_points_coord[i]['z']}\n")
        file.write('\n')
        file.write('\n')
        file.write('\n')

        # Part 2: Write LINES
        file.write('LINES NODE 1 - NODE 2\n')
        file.write('\n')
        file.write(str(len(all_elements_coord_connect)) + '\n')
        for i in all_elements_coord_connect:
            if i is None:
                continue
            file.write(
                f"{all_elements_coord_connect[i]['Point_0']['PointName']} {all_elements_coord_connect[i]['Point_f']['PointName']}\n")
        file.write('\n')
        file.write('\n')

        # Part 3: Write SENSORS
        file.write('SENSORS [ID, DIR (1-x, 2-y, 3-z)]\n')
        for i in range(len(sensors)):
            data = sensors[i]
            node = list(data)[0]
            dir_list = data[node]
            file.write(
                f'{node} {int(dir_list[0])} {int(dir_list[1])} {int(dir_list[2])}\n')

        file.write('\n')
        file.write('\n')
        file.write('\n')
        file.write('COLOR PLANE\n')
        file.write('\n')
        file.write('0')
        file.write('\n')
        file.write('\n')
