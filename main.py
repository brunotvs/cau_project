import datetime
import zoneinfo

import ee
import geemap.foliumap as geemap
import streamlit as st

import cau_project.algorithms as cau_algorithms
import cau_project.map as cau_map
import cau_project.palettes as cau_palettes
import cau_project.study_areas as cau_areas


def func(col):
    for i, date in enumerate(dates_list.getInfo() or []):
        (
            ee.ImageCollection(col)
            .filterDate(ee.Date(date["value"]))
            .mosaic()
            .aside(
                cau_map.add_layer_to_map(
                    {
                        "band": "shadow",
                        "min_max_strategy": cau_map.arbitrary_min_max(0, 1),
                        "name": f"shadow at {
                            datetime.datetime(
                                1970,
                                1,
                                1,
                                tzinfo=zoneinfo.ZoneInfo('America/Sao_Paulo'),
                            )
                            + datetime.timedelta(milliseconds=date['value'], hours=-3)
                        }",
                        "palette": cau_palettes.gray,
                    }
                ),
                Map,
            )
        )


st.set_page_config(layout="wide")
st.title("Interactive Earth Engine Dashboard")

ee.Initialize(project="earth-cau")

Map = geemap.Map(basemap="HYBRID")

region = (
    ee.FeatureCollection("FAO/GAUL/2025/level2")
    .filter(ee.Filter.eq("ADM1_NAME", "Sao Paulo"))
    .filter(ee.Filter.eq("ADM2_NAME", "Rio Grande Da Serra"))
)

region = ee.FeatureCollection(cau_areas.rgs)

Map.add_layer(
    ee_object=region.style(fillColor="0000", color="000F", width=5.0),
    vis_params={},
    name="First Level Administrative Units",
)

Map.center_object(region)

start_date = ee.Date("2023-01-01T00:00:00-03:00")
end_date = ee.Date("2023-01-02T00:00:00-03:00")


step_unit = "minute"
step_size = 1
n_dates = end_date.difference(start_date, step_unit).divide(step_size).floor()
dates_list = ee.List.sequence(0, n_dates).map(
    lambda d: start_date.advance(ee.Number(d).multiply(step_size), step_unit)
)


def create_empty_image(current_date):
    current_date = ee.Date(current_date)
    return ee.Image(
        ee.Image.constant(0).set(
            {
                "system:time_start": current_date.millis(),
            }
        )
    )


num_directions = 64
num_elevations = num_directions // 4
(
    ee.ImageCollection(dates_list.map(create_empty_image))
    .filterBounds(region)
    .map(cau_algorithms.dem())
    .map(cau_algorithms.building_height())
    .map(cau_algorithms.dsm())
    .map(
        cau_algorithms.svf(
            {
                "dsm_band": "dsm",
                "num_directions": num_directions,
                "num_elevations": num_elevations,
            }
        )
    )
    # .map(cau_algorithms.albedo())
    # .map(cau_algorithms.ndvi())
    # .map(
    #     cau_algorithms.ruggedness(
    #         {"height_band": "dsm", "radius": 45, "radius_units": "meters"}
    #     )
    # )
    # .map(cau_algorithms.lst())
    # .map(cau_algorithms.averaged_building_height())
    # .map(cau_algorithms.building_coverage_ratio())
    # .map(cau_algorithms.building_volume_density())
    .map(
        cau_algorithms.insolation(
            {"angular_precision": 1, "geometry": region.geometry()}
        )
    )
    .map(lambda img: img.clip(region))
    .map(
        lambda img: ee.Image(img).visualize(
            bands="shadow",
            min=0,
            max=1,
            forceRgbOutput=True,
        )
    )
    # .aside(func)
    .aside(
        lambda collection: geemap.ee_export_video_to_drive(
            collection=collection,
            description="rgs_shadows",
            folder="export",
            framesPerSecond=30,
            dimensions=720,
            region=region.geometry(),
        )
    )
)


default_geometry = region.geometry()  # ee.Geometry.BBox(-180, -90, 180, 90)
angular_precision = 10
bounds = default_geometry.bounds()
coords = ee.List(bounds.coordinates().get(0))

sw = ee.List(coords.get(0))
ne = ee.List(coords.get(2))

lon_min = ee.Number(sw.get(0)).max(-180)
lat_min = ee.Number(sw.get(1)).max(-90)
lon_max = ee.Number(ne.get(0)).min(180)
lat_max = ee.Number(ne.get(1)).min(90)

lons = ee.List.sequence(lon_min, lon_max, angular_precision)
lats = ee.List.sequence(lat_min, lat_max, angular_precision)

print(lon_min.getInfo())
print(lon_max.getInfo())
print(lat_min.getInfo())
print(lat_max.getInfo())
print(lons.getInfo())
print(lats.getInfo())


Map.to_streamlit(height=600)
