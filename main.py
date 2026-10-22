import ee
import geemap.foliumap as geemap
import streamlit as st

import cau_project.algorithms as cau_algorithms
import cau_project.map as cau_map
import cau_project.palettes as cau_palettes
import cau_project.study_areas as cau_areas
import cau_project.indicators as cau_indicators

ee.Initialize(project="earth-cau")


st.set_page_config(layout="wide")
st.title("Interactive Earth Engine Dashboard")


Map = geemap.Map(basemap="HYBRID")


region = (
    ee.FeatureCollection("FAO/GAUL/2025/level2")
    .filter(ee.Filter.eq("GAUL1_NAME", "São Paulo"))
    .filter(ee.Filter.eq("GAUL2_NAME", "Rio Grande Da Serra"))
)

region = ee.FeatureCollection(cau_areas.rgs)


Map.add_layer(
    ee_object=region.style(fillColor="0000", color="000F", width=5.0),
    vis_params={},
    name="First Level Administrative Units",
)

grid = region.geometry().coveringGrid(proj=ee.Projection("EPSG:31983"), scale=100)

Map.add_layer(
    ee_object=grid.style(fillColor="0000", color="000F", width=5.0),
    vis_params={},
    name="Grid",
)

Map.center_object(region)

day = ee.Date("2023-01-01T16:00:00-03:00")

y, d, m = cau_indicators.indicators(region.geometry(), day, 2**4, 15, "minute", 100)


y.aside(
    lambda img: [
        cau_map.add_layer_to_map(
            {
                "band": band,
                "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
            }
        )(img.clip(region), Map)
        for band in img.select("abh").bandNames().getInfo()
    ]
)

Map.to_streamlit(height=600)
