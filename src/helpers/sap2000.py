
from collections import defaultdict
import comtypes.client
import numpy as np
import warnings

import helpers.outils as outils


def raise_warning(process_name, ret) -> None:
    """
    Raise warning if ret=1
    """
    if ret == 1:
        message = process_name + ' was not properly retrieved in SAP2000'
        warnings.warn(message, UserWarning)


def app_start(use_GUI=True):
    """
    Function duties:
        Starts sap2000 application
    """
    # create API helper object
    helper = comtypes.client.CreateObject('SAP2000v1.Helper')
    helper = helper.QueryInterface(comtypes.gen.SAP2000v1.cHelper)
    mySapObject = helper.CreateObjectProgID("CSI.SAP2000.API.SapObject")

    # start SAP2000 application
    mySapObject.ApplicationStart(3, use_GUI, "")

    return mySapObject


def open_file(mySapObject, FilePath):
    """
    Function duties:
        Once the application has started, open an existing SAP2000 file
    """
    # create SapModel object
    SapModel = mySapObject.SapModel

    # initialize model
    ret = SapModel.InitializeNewModel()
    raise_warning('Initialize SAP2000', ret)

    # open existing file
    ret = SapModel.File.OpenFile(FilePath)
    raise_warning('Open file', ret)

    return SapModel


def unlock_model(SapModel, lock=False) -> None:
    """
    Function duties:
        If lock=False: unlocks model
        Else: locks model
    """
    ret = SapModel.SetModelIsLocked(False)
    if lock:
        raise_warning("Unlock", ret)
    else:
        raise_warning("Lock", ret)


def get_point_obj_names(SapModel):
    """
    Retrieves the names of all defined point (joint) objects in the SAP2000 model.

    Parameters:
        SapModel: COM object from SAP2000 API (e.g., SapObject.SapModel)

    Returns:
        all_points (list): List of all point object names in the model

    Raises:
        RuntimeError: If the retrieval fails
    """
    NumberNames = 0
    MyName = []
    output = SapModel.PointObj.GetNameList()
    NumberNames, MyName, ret = output
    raise_warning('Get all point names', ret)

    # Return as list
    return list(MyName)


def get_frame_obj_names(SapModel):
    """
    Retrieves the names of all defined frame (line) objects in the SAP2000 model.

    Parameters:
        SapModel: COM object from SAP2000 API (e.g., SapObject.SapModel)

    Returns:
        all_frames (list): List of all frame object names in the model

    Raises:
        RuntimeError: If the retrieval fails
    """
    NumberNames = 0
    FrameNames = []
    output = SapModel.FrameObj.GetNameList()
    NumberNames, FrameNames, ret = output
    raise_warning('Get all frame names', ret)

    # Return as list
    return list(FrameNames)


def get_frameconnectivity(all_points, all_elements,
                          SapModel, all_points_coord={}):
    """
    Function duties:
        For each frame, it gives initial and end point names;
        If all_points_coord dictionary is introduced, also coordinates of each point are provided
    Input:
        all_points: list with all points
        all_elements: list with all elements
        all_points_coord: if provided, dict containing x, y, z coordinates for each point
            (this dictionary comes from sap2000_getpointcoordinates function)
    """
    if len(all_points_coord) > 0:
        coord_defined = True
    else:
        coord_defined = False

    frames_dict = dict()
    key_ini, key_end = 'Point_0', 'Point_f'
    keys = [key_ini, key_end]
    for element in outils.sort_list_string(all_elements):
        frames_dict[element] = {key: None for key in keys}

    for PointName in all_points:
        NumberItems = 0
        ObjectType, ObjectName, PointNumber = [], [], []
        output = SapModel.PointObj.GetConnectivity(PointName, NumberItems,
                                                   ObjectType, ObjectName, PointNumber)
        [NumberItems, ObjectType, ObjectName, PointNumber, ret] = output
        raise_warning('Get connectivity', ret)

        # element_joint_connect = dict()
        ObjectType, ObjectName, PointNumber = list(
            ObjectType), list(ObjectName), list(PointNumber)
        FRAME_ID = 2  # stablished by SAP2000
        OBJECT_INI, OBJECT_END = 1, 2  # stablished by SAP2000

        # Retrieve frames (other elements could be connected)
        frames = [name for i, name in enumerate(
            ObjectName) if ObjectType[i] == FRAME_ID]

        for i, frame in enumerate(frames):
            coord = {}
            if PointNumber[i] == OBJECT_INI:
                if frames_dict[frame][key_ini] is None:
                    if coord_defined:
                        coord = all_points_coord[PointName]
                    frames_dict[frame][key_ini] = {
                        **{'PointName': PointName}, **coord}
                else:
                    if frames_dict[frame][key_ini] != PointName:
                        message = f'{frame} frame has 2 different {key_ini} assigments: ({PointName} and {frames_dict[frame][key_ini]}) '
                        warnings.warn(message, UserWarning)
            elif PointNumber[i] == OBJECT_END:
                if frames_dict[frame][key_end] is None:
                    if coord_defined:
                        coord = all_points_coord[PointName]
                    frames_dict[frame][key_end] = {
                        **{'PointName': PointName}, **coord}
                else:
                    if frames_dict[frame][key_end] != PointName:
                        message = f'{frame} frame has 2 different {key_end} assigments: ({PointName} and {frames_dict[frame][key_end]}) '
                        warnings.warn(message, UserWarning)

    return frames_dict


def get_pointcoordinates(all_points, SapModel, round_coordinates=True):
    """
    Function duties:
        Returns a dictionary with x-y-z coordinates for each point
        in all_points list
    Input:
        round_coordinates: if True, coordinates are rounded to 6 significant digits
            (Otherwise, some values could have very small variations)
    """
    pointcoord_dict = dict()
    for point in outils.sort_list_string(all_points):
        pointcoord_dict[point] = dict()
        x, y, z = 0, 0, 0
        output = SapModel.PointObj.GetCoordCartesian(point, x, y, z)
        [x, y, z, ret] = output
        raise_warning('Point coordinates', ret)

        if round_coordinates:
            x = outils.round_6_sign_digits(x)
            y = outils.round_6_sign_digits(y)
            z = outils.round_6_sign_digits(z)

        pointcoord_dict[point]['x'] = x
        pointcoord_dict[point]['y'] = y
        pointcoord_dict[point]['z'] = z

    return pointcoord_dict


def get_units(SapModel):
    """
    Retrieves the current working units set in the SAP2000 model.

    Returns
    -------
    units_code : int
        The numerical unit code as defined by SAP2000's `eUnits` enumeration.

    units_name : str
        Name of the current unit setting.

    The following unit codes are possible:

        1  → lb_in_F     (Pound, Inch, Fahrenheit)
        2  → lb_ft_F     (Pound, Foot, Fahrenheit)
        3  → kip_in_F    (Kip, Inch, Fahrenheit)
        4  → kip_ft_F    (Kip, Foot, Fahrenheit)
        5  → kN_mm_C     (kN, Millimeter, Celsius)
        6  → kN_m_C      (kN, Meter, Celsius)
        7  → kgf_mm_C    (kgf, Millimeter, Celsius)
        8  → kgf_m_C     (kgf, Meter, Celsius)
        9  → N_mm_C      (Newton, Millimeter, Celsius)
        10 → N_m_C       (Newton, Meter, Celsius)
        11 → Ton_mm_C    (Ton, Millimeter, Celsius)
        12 → Ton_m_C     (Ton, Meter, Celsius)
        13 → kN_cm_C     (kN, Centimeter, Celsius)
        14 → kgf_cm_C    (kgf, Centimeter, Celsius)
        15 → N_cm_C      (Newton, Centimeter, Celsius)
        16 → Ton_cm_C    (Ton, Centimeter, Celsius)
    """
    # Map of SAP2000 unit codes to human-readable names
    unit_names = {
        1: 'lb_in_F',
        2: 'lb_ft_F',
        3: 'kip_in_F',
        4: 'kip_ft_F',
        5: 'kN_mm_C',
        6: 'kN_m_C',
        7: 'kgf_mm_C',
        8: 'kgf_m_C',
        9: 'N_mm_C',
        10: 'N_m_C',
        11: 'Ton_mm_C',
        12: 'Ton_m_C',
        13: 'kN_cm_C',
        14: 'kgf_cm_C',
        15: 'N_cm_C',
        16: 'Ton_cm_C'
    }

    units_code = SapModel.GetPresentUnits()
    units_name = unit_names.get(units_code, f"Unknown ({units_code})")

    return units_code, units_name


def set_units(SapModel, units: int) -> None:
    """
    Sets the working units in SAP2000 using the provided unit code.

    Parameters
    ----------
    SapModel : object
        The active SAP2000 model object (cSapModel).

    units : int
        Unit code as defined in the SAP2000 eUnits enumeration.
        Valid values are:
            1  → lb_in_F     (Pound, Inch, Fahrenheit)
            2  → lb_ft_F     (Pound, Foot, Fahrenheit)
            3  → kip_in_F    (Kip, Inch, Fahrenheit)
            4  → kip_ft_F    (Kip, Foot, Fahrenheit)
            5  → kN_mm_C     (kN, Millimeter, Celsius)
            6  → kN_m_C      (kN, Meter, Celsius)
            7  → kgf_mm_C    (kgf, Millimeter, Celsius)
            8  → kgf_m_C     (kgf, Meter, Celsius)
            9  → N_mm_C      (Newton, Millimeter, Celsius)
            10 → N_m_C       (Newton, Meter, Celsius)
            11 → Ton_mm_C    (Ton, Millimeter, Celsius)
            12 → Ton_m_C     (Ton, Meter, Celsius)
            13 → kN_cm_C     (kN, Centimeter, Celsius)
            14 → kgf_cm_C    (kgf, Centimeter, Celsius)
            15 → N_cm_C      (Newton, Centimeter, Celsius)
            16 → Ton_cm_C    (Ton, Centimeter, Celsius)

    Raises
    ------
    Warning if setting units fails (non-zero return code).
    """
    ret = SapModel.SetPresentUnits(units)
    raise_warning('setting units', ret)


def set_kN_m_C_units(SapModel) -> None:
    """
    Function Duties:
        Sets units in kN, m, C
    Remark:
        Equivalent to use set_units(SapModel, 6)
    """
    set_kN_m_C = 6
    ret = SapModel.SetPresentUnits(set_kN_m_C)
    raise_warning('setting units', ret)


def get_point_forces(Name_points_group, SapModel, load_pattern=None,
                     return_kN=False):
    """
    Function Duties:
        Retrieves forces applied to a group of points in the model.
    Input:
        Name_points_group: Name of the group of points in the model
        SapModel: SAP2000 model object
        load_pattern: if specified, only retrieves results for it
            (default is None, which retrieves all load patterns)
        return_kN: if True, the function will convert the units to kN
    Output:
        output_dict: Dictionary with the forces applied to the points
            in the group
    """
    if return_kN:
        actual_units, _ = get_units(SapModel)
        set_kN_m_C_units(SapModel)

    PointName = ""
    NumberItems = 0
    LoadPat = ""
    LCStep = []
    CSys = []
    F1 = []
    F2 = []
    F3 = []
    M1 = []
    M2 = []
    M3 = []
    ItemType = 1  # 1 for Group, 1 for Object

    output = SapModel.PointObj.GetLoadForce(
        Name_points_group, NumberItems, PointName, LoadPat, LCStep, CSys, F1, F2, F3, M1, M2, M3, ItemType
    )

    [NumberItems, PointName, LoadPat, LCStep,
        CSys, F1, F2, F3, M1, M2, M3, ret] = output

    raise_warning('Get point forces', ret)

    if not (load_pattern is None):
        bool = [i == load_pattern for i in list(LoadPat)]
    else:
        bool = [True for i in list(LoadPat)]

    PointName = [PointName[i] for i, b in enumerate(bool) if b]
    LoadPat = [LoadPat[i] for i, b in enumerate(bool) if b]
    F1 = [F1[i] for i, b in enumerate(bool) if b]
    F2 = [F2[i] for i, b in enumerate(bool) if b]
    F3 = [F3[i] for i, b in enumerate(bool) if b]
    M1 = [M1[i] for i, b in enumerate(bool) if b]
    M2 = [M2[i] for i, b in enumerate(bool) if b]
    M3 = [M3[i] for i, b in enumerate(bool) if b]

    output_dict = {'PointObj': PointName, 'LoadPat': LoadPat,
                   'F1': F1, 'F2': F2, 'F3': F3,
                   'M1': M1, 'M2': M2, 'M3': M3}

    # Restore the original units
    if return_kN:
        set_units(SapModel, actual_units)

    return output_dict
