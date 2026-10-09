import hashlib
import warnings
from io import BytesIO
from pathlib import Path

import cartopy.crs as ccrs
import ee
import matplotlib.pyplot as plt
import numpy as np
import rasterio
import requests
from geemap.basemaps import custom_tiles
from geemap.cartoee import *
from matplotlib import colorbar
from shapely.geometry import shape

CACHE_DIR = Path(".ee_cache/")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def ee_hash(obj: ee.ComputedObject) -> str:
    serialized = obj.serialize()  # string JSON do grafo de computação
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _to_list(v, n=None):
    """Aceita número, lista ou string 'a,b,c' e devolve lista de floats."""
    if v is None:
        return None
    if isinstance(v, str):
        v = [float(i) for i in v.split(",")]
    elif isinstance(v, (int, float)):
        v = [float(v)]
    else:
        v = [float(i) for i in v]
    if n and len(v) == 1:
        v = v * n
    return v


def get_minimal_map(proj=None, basemap=None, zoom_level=2, **kwargs):

    if proj is None:
        proj = ccrs.PlateCarree()

    kwargs.pop("style", None)

    ax = plt.axes(projection=proj)

    if basemap is not None:
        if isinstance(basemap, str) and basemap.upper() in [
            "ROADMAP",
            "SATELLITE",
            "TERRAIN",
            "HYBRID",
        ]:
            basemap = cimgt.GoogleTiles(url=custom_tiles["xyz"][basemap.upper()]["url"])

        try:
            ax.add_image(basemap, zoom_level)
        except Exception as e:  # noqa: BLE001
            print("Failed to add basemap: ", e)

    return ax


def add_image_layer(ax, ee_object: ee.Image, dims=1000, vis_params=None, **kwargs):

    if type(ee_object) is not ee.image.Image:
        raise ValueError("provided `ee_object` is not of type ee.Image")

    if type(dims) not in [list, tuple, int]:
        raise ValueError("provided dims not of type list, tuple, or int")

    if type(ax) not in [GeoAxes, GeoAxesSubplot]:
        raise ValueError(
            "provided axes not of type cartopy.mpl.geoaxes.GeoAxes "
            "or cartopy.mpl.geoaxes.GeoAxesSubplot"
        )

    NODATA = -9999
    vis_params = dict(vis_params or {})

    bands = vis_params.get("bands")
    if bands:
        if isinstance(bands, str):
            bands = [b.strip() for b in bands.split(",")]
        ee_object = ee_object.select(bands)

    img = ee_object.toFloat().unmask(NODATA)

    hash = ee_hash(ee_object)
    print(hash)

    url = img.getDownloadURL(
        {
            "format": "GEO_TIFF",
            "crs": "EPSG:4326",
            "dimensions": dims,
        }
    )
    r = requests.get(url)
    r.raise_for_status()

    with open(CACHE_DIR / "saida.tif", "wb") as f:
        f.write(r.content)

    with rasterio.open(BytesIO(r.content)) as src:
        data = np.moveaxis(src.read().astype(float), 0, -1)
        b = src.bounds
        view_extent = (b.left, b.right, b.bottom, b.top)

    data[data == NODATA] = np.nan
    nb = data.shape[-1]

    # --- parâmetros de visualização ---
    vmin = _to_list(vis_params.get("min"), nb) or [
        np.nanmin(data[..., i]) for i in range(nb)
    ]
    vmax = _to_list(vis_params.get("max"), nb) or [
        np.nanmax(data[..., i]) for i in range(nb)
    ]
    gamma = _to_list(vis_params.get("gamma"), nb) or [1.0] * nb
    alpha = vis_params.get("opacity", 1)

    if nb >= 3:
        # composição RGB
        rgb = np.empty(data.shape[:2] + (3,))
        for i in range(3):
            band = (data[..., i] - vmin[i]) / (vmax[i] - vmin[i])
            rgb[..., i] = np.clip(band, 0, 1) ** (1 / gamma[i])
        ax.imshow(
            np.ma.masked_invalid(rgb),
            extent=view_extent,
            origin="upper",
            transform=ccrs.PlateCarree(),
            zorder=1,
            alpha=alpha,
        )
    else:
        # banda única: colormap + norm
        band = np.ma.masked_invalid(data[..., 0])

        pal = vis_params["palette"]
        if isinstance(pal, str):
            pal = pal.split(",")
        pal = [p if p.startswith("#") else "#" + p for p in pal]
        cm = colors.LinearSegmentedColormap.from_list("custom", pal, N=256)

        if gamma[0] != 1:
            norm = colors.PowerNorm(gamma=1 / gamma[0], vmin=vmin[0], vmax=vmax[0])
        else:
            norm = colors.Normalize(vmin=vmin[0], vmax=vmax[0])

        ax.imshow(
            band,
            cmap=cm,
            norm=norm,
            extent=view_extent,
            origin="upper",
            transform=ccrs.PlateCarree(),
            zorder=1,
            alpha=alpha,
        )

    return ax


def add_colorbar(
    ax, vis_params, loc=None, cmap="gray", discrete=False, label=None, **kwargs
):
    """
    Add a colorbar to the map based on visualization parameters provided
    args:
        ax (cartopy.mpl.geoaxes.GeoAxesSubplot | cartopy.mpl.geoaxes.GeoAxes): required cartopy GeoAxesSubplot object to add image overlay to
        loc (str, optional): string specifying the position
        vis_params (dict, optional): visualization parameters as a dictionary. See https://developers.google.com/earth-engine/guides/image_visualization for options.
        **kwargs: remaining keyword arguments are passed to colorbar()

    raises:
        Warning: If 'discrete' is true when "palette" key is not in visParams
        ValueError: If `ax` is not of type cartopy.mpl.geoaxes.GeoAxesSubplot
        ValueError: If 'cmap' or "palette" key in visParams is not provided
        ValueError: If "min" in visParams is not of type scalar
        ValueError: If "max" in visParams is not of type scalar
        ValueError: If 'loc' or 'cax' keywords are not provided
        ValueError: If 'loc' is not of type str or does not equal available options
    """

    if type(ax) not in [GeoAxes, GeoAxesSubplot]:
        raise ValueError(
            "provided axes not of type cartopy.mpl.geoaxes.GeoAxes "
            "or cartopy.mpl.geoaxes.GeoAxesSubplot"
        )

    if loc:
        if (type(loc) == str) and (loc in ["left", "right", "bottom", "top"]):
            if "posOpts" not in kwargs:
                posOpts = {
                    "left": [0.01, 0.25, 0.02, 0.5],
                    "right": [0.88, 0.25, 0.02, 0.5],
                    "bottom": [0.25, 0.15, 0.5, 0.02],
                    "top": [0.25, 0.88, 0.5, 0.02],
                }
            else:
                posOpts = {
                    "left": kwargs["posOpts"],
                    "right": kwargs["posOpts"],
                    "bottom": kwargs["posOpts"],
                    "top": kwargs["posOpts"],
                }
                del kwargs["posOpts"]

            cax = ax.figure.add_axes(posOpts[loc])

            if loc == "left":
                plt.subplots_adjust(left=0.18)
            elif loc == "right":
                plt.subplots_adjust(right=0.85)
            else:
                pass

        else:
            raise ValueError(
                'provided loc not of type str. options are "left", '
                '"top", "right", or "bottom"'
            )

    elif "cax" in kwargs:
        cax = kwargs["cax"]
        kwargs = {key: kwargs[key] for key in kwargs if key != "cax"}

    else:
        raise ValueError("loc or cax keywords must be specified")

    vis_keys = list(vis_params.keys())
    norm = None
    alpha = None
    if vis_params:
        im = ax.images[-1] if ax.images else None
        clim = im.get_clim() if im is not None else (0, 1)

        if "min" in vis_params:
            vmin = vis_params["min"]
            if type(vmin) not in (int, float):
                raise ValueError("provided min value not of scalar type")
        else:
            vmin = float(clim[0])

        if "max" in vis_params:
            vmax = vis_params["max"]
            if type(vmax) not in (int, float):
                raise ValueError("provided max value not of scalar type")
        else:
            vmax = float(clim[1])

        if "opacity" in vis_params:
            alpha = vis_params["opacity"]
            if type(alpha) not in (int, float):
                raise ValueError("provided opacity value of not type scalar")
        elif "alpha" in kwargs:
            alpha = kwargs["alpha"]
        else:
            alpha = 1

        if cmap is not None:
            if discrete:
                warnings.warn(
                    'discrete keyword used when "palette" key is '
                    "supplied with visParams, creating a continuous "
                    "colorbar..."
                )

            cmap = plt.get_cmap(cmap)
            norm = colors.Normalize(vmin=vmin, vmax=vmax)

        if "palette" in vis_keys:
            hexcodes = vis_params["palette"]
            hexcodes = [i if i[0] == "#" else "#" + i for i in hexcodes]

            if discrete:
                cmap = colors.ListedColormap(hexcodes)
                vals = np.linspace(vmin, vmax, cmap.N + 1)
                norm = colors.BoundaryNorm(vals, cmap.N)

            else:
                cmap = colors.LinearSegmentedColormap.from_list(
                    "custom", hexcodes, N=256
                )
                norm = colors.Normalize(vmin=vmin, vmax=vmax)

        elif cmap is not None:
            if discrete:
                warnings.warn(
                    'discrete keyword used when "palette" key is '
                    "supplied with visParams, creating a continuous "
                    "colorbar..."
                )

            cmap = plt.get_cmap(cmap)
            norm = colors.Normalize(vmin=vmin, vmax=vmax)

        else:
            raise ValueError(
                'cmap keyword or "palette" key in visParams must be provided'
            )

    tick_font_size = None
    if "tick_font_size" in kwargs:
        tick_font_size = kwargs.pop("tick_font_size")

    label_font_family = None
    if "label_font_family" in kwargs:
        label_font_family = kwargs.pop("label_font_family")

    label_font_size = None
    if "label_font_size" in kwargs:
        label_font_size = kwargs.pop("label_font_size")

    cb = colorbar.ColorbarBase(cax, norm=norm, alpha=alpha, cmap=cmap, **kwargs)

    if label is not None:
        if label_font_size is not None and label_font_family is not None:
            cb.set_label(label, fontsize=label_font_size, family=label_font_family)
        elif label_font_size is not None and label_font_family is None:
            cb.set_label(label, fontsize=label_font_size)
        elif label_font_size is None and label_font_family is not None:
            cb.set_label(label, family=label_font_family)
        else:
            cb.set_label(label)
    elif "bands" in vis_keys:
        cb.set_label(vis_params["bands"])

    if tick_font_size is not None:
        cb.ax.tick_params(labelsize=tick_font_size)


def add_vector_layer(ax, fc, style=None, **kwargs):
    style = style or {}
    url = fc.getDownloadURL(filetype="geojson")
    r = requests.get(url)
    r.raise_for_status()
    geoms = [shape(f["geometry"]) for f in r.json()["features"]]

    ax.add_geometries(
        geoms,
        crs=ccrs.PlateCarree(),
        facecolor=style.get("fillColor", "none"),
        edgecolor=style.get("color", "black"),
        linewidth=style.get("width", 1),
        zorder=2,
        **kwargs,
    )
