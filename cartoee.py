import datetime
import math
import zoneinfo
from pathlib import Path

import ee
import geemap.foliumap as geemap
import matplotlib.pyplot as plt
from geemap import cartoee

import cau_project.algorithms as cau_algorithms
import cau_project.palettes as cau_palettes
import cau_project.study_areas as cau_areas


def format_date(date: int, tz: int = 0) -> str:
    dt = datetime.datetime(
        1970,
        1,
        1,
        tzinfo=zoneinfo.ZoneInfo("America/Sao_Paulo"),
    ) + datetime.timedelta(milliseconds=date, hours=tz)

    return dt.strftime("%Y-%m-%d")


def solar_radiation(curr: ee.ComputedObject, prev: ee.ComputedObject):
    curr = ee.Image(curr)
    prev = ee.Image(prev)
    prev_date = prev.date()

    curr_date = curr.date()

    delta_seconds = curr_date.difference(prev_date, "second")

    return (
        curr.multiply(delta_seconds)
        .add(prev)
        .rename("radiation")
        .copyProperties(curr, ["system:time_start", "system:time_end"])
    )


geemap.ee_initialize(project="earth-cau")


region = (
    ee.FeatureCollection("FAO/GAUL/2025/level2")
    .filter(ee.Filter.eq("ADM1_NAME", "Sao Paulo"))
    .filter(ee.Filter.eq("ADM2_NAME", "Rio Grande Da Serra"))
)

region = ee.FeatureCollection(cau_areas.rgs)


start_date = ee.Date("2023-01-01T16:00:00-03:00")
end_date = ee.Date("2023-01-01T16:00:00-03:00")


step_unit = "hour"
step_size = 1
mills_step = (
    start_date.advance(step_size, step_unit)
    .difference(start_date, "second")
    .multiply(1000)
)
dates = ee.List.sequence(start_date.millis(), end_date.millis(), mills_step)
dates = ee.List(
    [
        # ee.Date("2022-03-20T16:00:00-03:00").millis(),
        # ee.Date("2022-06-20T16:00:00-03:00").millis(),
        ee.Date("2023-09-22T16:00:00-03:00").millis(),
        # ee.Date("2023-12-21T16:00:00-03:00").millis(),
    ]
)


num_directions = 12
num_elevations = num_directions // 4
static_base = (
    ee.ImageCollection([ee.Image()])
    .map(
        lambda img: ee.Image(img).set(
            {
                "system:time_start": start_date.millis(),
            }
        )
    )
    .map(cau_algorithms.dem())
    .map(cau_algorithms.building_height())
    .map(cau_algorithms.dsm())
    # .map(cau_algorithms.walls({"threshold": 3}))
    # .map(
    #     cau_algorithms.svf(
    #         {
    #             "num_directions": num_directions,
    #             "num_elevations": num_elevations,
    #         }
    #     )
    # )
    # .map(cau_algorithms.albedo())
    # .map(cau_algorithms.emissivity())
    # .map(cau_algorithms.ndvi())
    # .map(cau_algorithms.ruggedness({"height_band": "dsm"}))
    # .map(cau_algorithms.averaged_building_height())
    # .map(cau_algorithms.building_coverage_ratio())
    # .map(cau_algorithms.building_volume_density({"radius": 200}))
    # .map(cau_algorithms.area())
    .first()
)

#
# def get_bbox(ee_object):
#     """Retorna uma lista [xmin, ymin, xmax, ymax] do BBOX de qualquer objeto do GEE."""
#     # Garante que funciona tanto para Geometry quanto para Feature ou FeatureCollection
#     geom = (
#         ee_object.geometry()
#         if hasattr(ee_object, "geometry")
#         else ee.Geometry(ee_object)
#     )
#
#     # Extrai o retângulo envolvente
#     coords = (geom.bounds().coordinates().getInfo() or [])[0]
#
#     # Retorna [xmin, ymin, xmax, ymax]
#     return [coords[0][0], coords[0][1], coords[2][0], coords[2][1]]


def auto_zoom(bbox, target_px=2000, min_zoom=10, max_zoom=19):
    """
    Pick a tile zoom level so the region spans roughly `target_px` pixels
    along its longest side.
    bbox: (west, south, east, north) in degrees.
    """
    west, south, east, north = bbox
    lat_mid = math.radians((south + north) / 2)

    # Extent in "world fractions" (0-1 across the full Mercator world)
    width_frac = (east - west) / 360
    height_frac = (north - south) / 360 / math.cos(lat_mid)  # approx. Mercator stretch

    longest = max(width_frac, height_frac)
    z = math.log2(target_px / (256 * longest))
    return max(min_zoom, min(max_zoom, round(z)))


def nice_length(bbox, fraction=0.2):
    """Scale bar length (km) of roughly `fraction` of the map width, rounded to 1/2/5 x 10^n."""
    west, south, east, north = bbox
    lat_mid = math.radians((south + north) / 2)
    width_km = abs(east - west) * 111.32 * math.cos(lat_mid)

    target = width_km * fraction
    exp = math.floor(math.log10(target))
    base = target / 10**exp
    nice = 1 if base < 1.5 else 2 if base < 3.5 else 5 if base < 7.5 else 10
    return nice * 10**exp


def figsize_from_bbox(bbox, long_side=10, extra_w=1.5):
    """
    Retorna (largura, altura) em polegadas, com o lado maior do mapa = long_side.
    extra_w: espaço extra na largura para colorbar e rótulos.
    """
    west, south, east, north = bbox
    w_deg = abs(east - west)
    h_deg = abs(north - south)
    ratio = w_deg / h_deg  # largura / altura

    if ratio >= 1:
        map_w, map_h = long_side, long_side / ratio
    else:
        map_w, map_h = long_side * ratio, long_side

    return (map_w + extra_w, map_h)


w, s, e, n = geemap.ee_to_bbox(region)
bbox = [e, s, w, n]
length_km = nice_length(bbox)
zoom = auto_zoom(bbox, target_px=2000)

band = "dsm"
img = ee.Image(static_base.select(band))


stats: dict = (
    img.reduceRegion(
        reducer=ee.Reducer.minMax(),
        geometry=region.geometry(),
        scale=30,
        bestEffort=True,
    ).getInfo()
    or {}
)

vmin = math.floor(stats[f"{band}_min"] / 10) * 10
vmax = math.ceil(stats[f"{band}_max"] / 10) * 10

vis = {
    "bands": [band],
    "min": vmin,
    "max": vmax,
    "palette": cau_palettes.qgis_terrain,
    "opacity": 0.8,
}

fig = plt.figure(figsize=figsize_from_bbox(bbox))


ax = cartoee.get_map(
    img.clip(region), region=bbox, vis_params=vis, basemap="HYBRID", zoom_level=zoom
)

cartoee.add_colorbar(
    ax, vis, loc="right", label="Elevation (m)", orientation="vertical"
)

cartoee.add_gridlines(ax, interval=0.005, xtick_rotation=45, linestyle=":")

# Optional extras:
cartoee.add_north_arrow(ax, text="N", xy=(1.1, 0.1), fontsize=20)
cartoee.add_scale_bar_lite(
    ax, length=length_km * 1000, xy=(0.8, 0.05), fontsize=20, unit="m", color="white"
)
cartoee.pad_view(ax)

ax.set_title("Digital Surface Model", fontsize=15)

output_dir = Path(".export/maps/")
output_dir.mkdir(parents=True, exist_ok=True)

cartoee.savefig(
    fig=fig,
    fname=output_dir / "teste",
)
