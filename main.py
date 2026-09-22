import datetime
import zoneinfo

import ee
import geemap.foliumap as geemap
import streamlit as st

import cau_project.algorithms as cau_algorithms
import cau_project.map as cau_map
import cau_project.palletes as cau_palletes

st.set_page_config(layout="wide")
st.title("Interactive Earth Engine Dashboard")

ee.Initialize(project="earth-cau")

Map = geemap.Map(basemap="HYBRID")

region = (
    ee.FeatureCollection("FAO/GAUL/2015/level2")
    .filter(ee.Filter.eq("ADM1_NAME", "Sao Paulo"))
    .filter(ee.Filter.eq("ADM2_NAME", "Rio Grande Da Serra"))
)

region = ee.FeatureCollection(
    ee.Geometry.Point([-46.39906192606612, -23.753554443082365]).buffer(50)
)

Map.add_layer(
    ee_object=region.style(fillColor="0000", color="000F", width=5.0),
    vis_params={},
    name="First Level Administrative Units",
)

Map.center_object(region)

start_date = ee.Date("2023-01-01T10:00:00-03:00")
end_date = ee.Date("2023-01-01T13:00:00-03:00")


step_unit = "hour"
step_size = 1
n_dates = end_date.difference(start_date, step_unit).divide(step_size).floor()
dates_list = ee.List.sequence(0, n_dates.subtract(1)).map(
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
    .map(cau_algorithms.building_heights())
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
    .map(cau_algorithms.albedo())
    .map(cau_algorithms.ndvi())
    .map(
        cau_algorithms.ruggedness(
            {"height_band": "dsm", "radius": 45, "radius_units": "meters"}
        )
    )
    .map(cau_algorithms.lst())
    .map(cau_algorithms.compactness({"radius": 100, "radius_units": "meters"}))
    .map(lambda img: img.clip(region))
    .aside(
        lambda col: [
            (
                ee.ImageCollection(col)
                .filterDate(ee.Date(date["value"]))
                .first()
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
                                + datetime.timedelta(
                                    milliseconds=date['value'], hours=-3
                                )
                            }",
                            "palette": cau_palletes.gray,
                        }
                    ),
                    Map,
                )
            )
            for i, date in enumerate(dates_list.getInfo() or [])
        ]
    )
)


Map.to_streamlit(height=600)
