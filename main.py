import ee
import geemap.foliumap as geemap
import streamlit as st

import cau_project.algorithms as cau_algorithms
import cau_project.map as cau_map

st.set_page_config(layout="wide")
st.title("Interactive Earth Engine Dashboard")

ee.Initialize(project="earth-cau")

Map = geemap.Map(basemap="HYBRID")

region = (
    ee.FeatureCollection("FAO/GAUL/2015/level2")
    .filter(ee.Filter.eq("ADM1_NAME", "Sao Paulo"))
    .filter(ee.Filter.eq("ADM2_NAME", "Rio Grande Da Serra"))
)

Map.add_layer(
    ee_object=region.style(fillColor="0000", color="000F", width=5.0),
    vis_params={},
    name="First Level Administrative Units",
)

Map.center_object(region)

start_date = ee.Date("2016-01-01T12:00:00-03:00")
end_date = ee.Date("2024-01-01T12:00:00-03:00")

step_unit = "day"
n_dates = end_date.difference(start_date, step_unit)
dates_list = ee.List.sequence(0, n_dates.subtract(1)).map(
    lambda d: start_date.advance(ee.Number(d), step_unit)
)


def create_empty_image(current_date):
    current_date = ee.Date(current_date)
    return ee.Image(
        ee.Image.constant(0).set(
            {
                "system:time_start": current_date.millis(),
                "date_formatted": current_date.format("YYYY-MM-dd"),
            }
        )
    )


dir = 16
(
    ee.ImageCollection(dates_list.map(create_empty_image))
    .filterBounds(region)
    .map(cau_algorithms.dem())
    .map(cau_algorithms.building_heights())
    .map(cau_algorithms.dsm())
    .map(
        cau_algorithms.svf(
            {"dsm_band": "dsm", "num_directions": dir, "num_elevations": dir // 4}
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
    # .map(cau_algorithms.shadow({"dem_band": "dsm", "neighborhood_size": 200}))
    .map(lambda img: img.clip(region))
    .aside(
        lambda col: [
            (
                ee.ImageCollection(col)
                .filterDate(ee.Date("2023-03-20").getRange("day"))
                .first()
                .aside(
                    cau_map.add_layer_to_map(
                        {
                            "band": "svf",
                            "min_max_strategy": cau_map.absolute_min_max(
                                region.geometry()
                            ),
                            "name": "svf",
                            # "palette": [
                            # "purple",
                            # "red",
                            # "yellow",
                            # "green",
                            # "#040274",
                            # "#040281",
                            # "#0502a3",
                            # "#0502b8",
                            # "#0502ce",
                            # "#0502e6",
                            # "#0602ff",
                            # "#235cb1",
                            # "#307ef3",
                            # "#269db1",
                            # "#30c8e2",
                            # "#32d3ef",
                            # "#3be285",
                            # "#3ff38f",
                            # "#86e26f",
                            # "#3ae237",
                            # "#b4e247",
                            # "#efff2a",
                            # "#ffc414",
                            # "#ff7f0e",
                            # "#ff4f00",
                            # "#ff0000",
                            # "#de0101",
                            # "#b20101",
                            # ],
                        }
                    ),
                    Map,
                )
            )
            for year in [
                2023
            ]  # dates_list.map(lambda d: ee.Date(d).get("year")).getInfo() or []
        ]
    )
)


Map.to_streamlit(height=600)
