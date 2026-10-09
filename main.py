import ee
import geemap.foliumap as geemap
import streamlit as st

import cau_project.algorithms as cau_algorithms
import cau_project.map as cau_map
import cau_project.palettes as cau_palettes
import cau_project.study_areas as cau_areas

st.set_page_config(layout="wide")
st.title("Interactive Earth Engine Dashboard")

ee.Initialize(project="earth-cau")

Map = geemap.Map(basemap="HYBRID")


region = (
    ee.FeatureCollection("FAO/GAUL/2025/level2")
    .filter(ee.Filter.eq("ADM1_NAME", "Sao Paulo"))
    .filter(ee.Filter.eq("ADM2_NAME", "Rio Grande Da Serra"))
)

region = ee.FeatureCollection(cau_areas.sjc)

Map.add_layer(
    ee_object=region.style(fillColor="0000", color="000F", width=5.0),
    vis_params={},
    name="First Level Administrative Units",
)


Map.center_object(region)

start_date = ee.Date("2023-01-01T16:00:00-03:00")
end_date = ee.Date("2023-01-01T16:00:00-03:00")


step_unit = "hour"
step_size = 1
n_dates = end_date.difference(start_date, step_unit).divide(step_size).floor()
dates_list = ee.List.sequence(0, n_dates).map(
    lambda d: start_date.advance(ee.Number(d).multiply(step_size), step_unit)
)

dates_list = ee.List([ee.Date("2023-12-23T16:00:00-03:00")])


def create_empty_image(current_date):
    current_date = ee.Date(current_date)
    return ee.Image(
        ee.Image.constant(0).set(
            {
                "system:time_start": current_date.millis(),
            }
        )
    )


(
    ee.ImageCollection(dates_list.map(create_empty_image))
    .filterBounds(region)
    .map(cau_algorithms.urban_area())
    .map(cau_algorithms.lst())
    .map(cau_algorithms.heat_island_intensity({"geometry": region.geometry()}))
    .map(lambda img: img.clip(region))
    .first()
    .aside(
        cau_map.add_layer_to_map(
            {
                "band": "heat_island_intensity",
                "palette": cau_palettes.qgis_ylorrd,
                "min_max_strategy": cau_map.arbitrary_min_max(-5, 15),
            }
        ),
        Map,
    )
    .aside(
        lambda img: Map.add_colorbar(
            {
                "bands": "heat_island_intensity",
                "palette": cau_palettes.qgis_ylorrd,
                "min": -5,
                "max": 15,
            }
        )
    )
)


Map.to_streamlit(height=600)
