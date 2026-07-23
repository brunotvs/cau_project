# python libraries
import numpy as np


def horizon_shift_vector(num_directions=16, radius_pixels=10, min_radius=1):
    # Initialize the output dict
    shift = {}

    # Generate angles and corresponding normal shifts in X (columns)
    # and Y (lines) direction
    angles = (2 * np.pi / num_directions) * np.arange(num_directions)
    x = np.cos(angles)
    y = np.sin(angles)
    angles = np.round(np.degrees(angles), decimals=1)

    # Generate a range of radius values in pixels.
    # Make it finer for the selected scaling.
    # By adding the last constant we make sure that we do not start with
    # point (0,0).
    scale = 3.0
    radii = np.arange((radius_pixels - min_radius) * scale + 1) / scale + min_radius

    # For each direction compute all possible horizon point position
    # and round them to integers
    for i in range(num_directions):
        x_int = np.round(x[i] * radii, decimals=0)
        y_int = np.round(y[i] * radii, decimals=0)
        # consider only the minimal number of points
        # use the trick with set and complex number as the input
        coord_complex = set(x_int + 1j * y_int)
        # to sort proportional with increasing radius,
        # set has to be converted to numpy array
        shift_pairs = np.array([(k.real, k.imag) for k in coord_complex]).astype(int)
        distance = np.sqrt(np.sum(shift_pairs**2, axis=1))
        sort_index = np.argsort(distance)
        # write for each direction shifts and corresponding distances
        shift[angles[i]] = {
            "shift": [(k[0], k[1]) for k in shift_pairs[sort_index]],
            "distance": distance[sort_index],
        }

    return shift


def sky_view_factor_compute(
    height_arr,
    radius_max=10,
    radius_min=1,
    num_directions=16,
    compute_svf=True,
    compute_opns=False,
    compute_asvf=False,
    a_main_direction=315.0,
    a_poly_level=4,
    a_min_weight=0.4,
):
    """
    Calculates horizon based visualizations: Sky-view factor, Anisotropic SVF and Openness.

    SVF processing is using search radius, that looks at values beyond the edge of an array. Consider using a buffered
    array as an input, with the buffer size equal to the radius_max.
    To prevent erosion of the edge, function applies mirrored padding in all four directions, however, this means that
    edge values are "averaged over half of the hemisphere". Similarly, the edges of the dataset (i.e. areas with NaN
    values), will be considered as fully open (SFV angle 0, Openness angle -90).

    Input array should use np.nan as nodata value.

    Parameters
    ----------
    height_arr : numpy.ndarray
        Elevation (DEM) as 2D numpy array.
    radius_max : int
        Maximal search radius in pixels/cells (not in meters).
    radius_min : int
        Minimal search radius in pixels/cells (not in meters), for noise reduction.
    num_directions : int
        Number of directions as input.
    compute_svf : bool
        If true it computes and outputs svf.
    compute_asvf : bool
        If true it computes and outputs asvf.
    compute_opns : bool
        If true it computes and outputs opns.
    a_main_direction : int or float
        Main direction of anisotropy.
    a_poly_level : int
        Level of polynomial that determines the anisotropy.
    a_min_weight : float
        Weight to consider anisotropy:
                 0 - low anisotropy,
                 1 - high  anisotropy (no illumination from the direction opposite the main direction)

    Returns
    -------
    dict_out : dictionary
        Return {"svf": svf_out, "asvf": asvf_out, "opns": opns_out};
        svf_out, skyview factor : 2D numpy array (numpy.ndarray) of skyview factor;
        asvf_out, anisotropic skyview factor : 2D numpy array (numpy.ndarray) of anisotropic skyview factor;
        opns_out, openness : 2D numpy array (numpy.ndarray) openness (elevation angle of horizon).
    """

    # Pad the array for the radius_max on all 4 sides
    height = np.pad(height_arr, radius_max, mode="reflect")

    # Compute the vector of movement and corresponding distances
    move = horizon_shift_vector(
        num_directions=num_directions, radius_pixels=radius_max, min_radius=radius_min
    )

    # Initiate the output for SVF
    if compute_svf:
        svf_out = (
            height * 0
        )  # Multiply with 0 instead of using np.zeros to preserve nodata
    else:
        svf_out = None

    # Initiate the output for azimuth dependent SVF
    if compute_asvf:
        asvf_out = (
            height * 0
        )  # Multiply with 0 instead of using np.zeros to preserve nodata
        w_m = a_min_weight
        w_a = np.deg2rad(a_main_direction)
        weight = np.arange(num_directions) * (2 * np.pi / num_directions)
        weight = (1 - w_m) * (np.cos((weight - w_a) / 2)) ** a_poly_level + w_m
    else:
        asvf_out = None
        weight = None

    # Initiate the output for Openness
    if compute_opns:
        opns_out = (
            height * 0
        )  # Multiply with 0 instead of using np.zeros to preserve nodata
    else:
        opns_out = None

    # Search for horizon in each direction...
    for i_dir, direction in enumerate(move):
        # Reset maximum at each iteration (i.e. at the start of new direction),
        # smallest possible elevation angle is -1000 rad (i.e. -90 deg)
        max_slope = np.zeros(height.shape, dtype=np.float32) - 1000

        # ... and for each search radius
        for i_rad, radius in enumerate(move[direction]["distance"]):
            # Get shift index from move dictionary
            shift_indx = move[direction]["shift"][i_rad]
            # Estimate the slope
            _ = (np.roll(height, shift_indx, axis=(0, 1)) - height) / radius
            # Compare to the previous max slope and keep the largest values (element wise). Use np.fmax to prevent NaN
            # values contaminating the edge of the image (if one of the elements is NaN, pick non-NaN element)
            max_slope = np.fmax(max_slope, _)

        # Convert to angle in radians and compute directional output
        max_slope = np.arctan(max_slope)

        # Sum max angle for all directions
        if compute_svf:
            # For SVF minimum possible angle is 0 (hemisphere), use np.fmax() to change NaNs to 0
            svf_out = svf_out + (1 - np.sin(np.fmax(max_slope, 0)))
        if compute_asvf:
            # For SVF minimum possible angle is 0 (hemisphere), use np.fmax() to change NaNs to 0
            asvf_out = asvf_out + (1 - np.sin(np.fmax(max_slope, 0))) * weight[i_dir]
        if compute_opns:
            # For Openness taking the entire sphere
            opns_out = opns_out + max_slope

    # Cut to original extent and average the directional output over all directions
    if compute_svf:
        svf_out = (
            svf_out[radius_max:-radius_max, radius_max:-radius_max] / num_directions
        )
    if compute_asvf:
        asvf_out = asvf_out[radius_max:-radius_max, radius_max:-radius_max] / np.sum(
            weight
        )
    if compute_opns:
        opns_out = np.rad2deg(
            0.5 * np.pi
            - (
                opns_out[radius_max:-radius_max, radius_max:-radius_max]
                / num_directions
            )
        )

    # Return results within dict
    dict_svf_asvf_opns = {"svf": svf_out, "asvf": asvf_out, "opns": opns_out}
    dict_svf_asvf_opns = {
        k: v for k, v in dict_svf_asvf_opns.items() if v is not None
    }  # filter out none

    return dict_svf_asvf_opns


def sky_view_factor(
    dem,
    resolution,
    compute_svf=True,
    compute_opns=False,
    compute_asvf=False,
    svf_n_dir=16,
    svf_r_max=10,
    svf_noise=0,
    asvf_dir=315,
    asvf_level=1,
    ve_factor=1,
    no_data=None,
):
    """
    Prepare the data, call sky_view_factor_compute, reformat and return back 2D arrays.

    Parameters
    ----------
    dem : numpy.ndarray
        Input digital elevation model as 2D numpy array.
    compute_svf : bool
        Compute SVF (True) or not (False).
    compute_opns : bool
        Compute OPENNESS (True) or not (False).
    resolution : float
        Pixel resolution.
    svf_n_dir : int
        Number of directions.
    svf_r_max : int
        Maximal search radius in pixels.
    svf_noise : int
        The level of noise remove (0-don't remove, 1-low, 2-med, 3-high).
    compute_asvf : bool
        Compute anisotropic SVF (True) or not (False).
    asvf_level : int
        Level of anisotropy, 1-low, 2-high.
    asvf_dir : int or float
        Direction of anisotropy.
    ve_factor : int or float
        Vertical exaggeration factor.
    no_data : int or float
        Value that represents no_data, all pixels with this value are changed to np.nan. Use this parameter when nodata
        is not np.nan.

    Returns
    -------
    dict_out : dictionary
        Return {"svf": svf_out, "asvf": asvf_out, "opns": opns_out};
        svf_out, skyview factor : 2D numpy array (numpy.ndarray) of skyview factor;
        asvf_out, anisotropic skyview factor : 2D numpy array (numpy.ndarray) of anisotropic skyview factor;
        opns_out, openness : 2D numpy array (numpy.ndarray) openness (elevation angle of horizon).
    """

    # Checks for input parameters
    if dem.ndim != 2:
        raise Exception("rvt.visualization.sky_view_factor: dem has to be 2D np.array!")
    if not (10000 >= ve_factor >= -10000):
        raise Exception(
            "rvt.visualization.sky_view_factor: ve_factor must be between -10000 and 10000!"
        )
    if svf_noise != 0 and svf_noise != 1 and svf_noise != 2 and svf_noise != 3:
        raise Exception(
            "rvt.visualization.sky_view_factor: svf_noise must be one of the following"
            "values (0-don't remove, 1-low, 2-med, 3-high)!"
        )
    if asvf_level != 1 and asvf_level != 2:
        raise Exception(
            "rvt.visualization.sky_view_factor: asvf_leve must be one of the following"
            "values (1-low, 2-high)!"
        )
    if not compute_svf and not compute_asvf and not compute_opns:
        raise Exception("rvt.visualization.sky_view_factor: All computes are false!")
    if resolution < 0:
        raise Exception(
            "rvt.visualization.sky_view_factor: resolution must be a positive number!"
        )

    # Make sure array has the correct dtype!
    dem = dem.astype(np.float32)

    # CONSTANTS
    # Level of polynomial that determines the anisotropy, selected with asvf_level (1 - low, 2 - high)
    sc_asvf_pol = [4, 8]
    sc_asvf_min = [0.4, 0.1]
    # The portion (percent) of the maximal search radius to ignore in horizon estimation; for each noise level,
    # selected with svf_noise (0-3)
    sc_svf_r_min = [0.0, 10.0, 20.0, 40.0]

    # Before doing anything to the array, make sure all NODATA values are set to np.nan
    if no_data is not None:
        dem[dem == no_data] = np.nan
    # Save NaN mask (processing may change NaNs to arbitrary values)
    nan_mask = np.isnan(dem)

    # Vertical exaggeration
    dem = dem * ve_factor
    # Pixel size (adjust elevation to correctly calculate the vertical elevation angle, calculation thinks 1px == 1m)
    dem = dem / resolution

    # Minimal search radius depends on the noise level, it has to be an integer not smaller than 1
    svf_r_min = max(np.round(svf_r_max * sc_svf_r_min[svf_noise] * 0.01, decimals=0), 1)

    # Set anisotropy parameters
    poly_level = sc_asvf_pol[asvf_level - 1]
    min_weight = sc_asvf_min[asvf_level - 1]

    # Main routine for SVF processing
    dict_svf_asvf_opns = sky_view_factor_compute(
        height_arr=dem,
        radius_max=svf_r_max,
        radius_min=svf_r_min,
        num_directions=svf_n_dir,
        compute_svf=compute_svf,
        compute_opns=compute_opns,
        compute_asvf=compute_asvf,
        a_main_direction=asvf_dir,
        a_poly_level=poly_level,
        a_min_weight=min_weight,
    )

    # Apply NaN mask to outputs
    for item in dict_svf_asvf_opns.values():
        item[nan_mask] = np.nan

    return dict_svf_asvf_opns
