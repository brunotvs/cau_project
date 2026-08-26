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

# region = ee.FeatureCollection(
#     [ee.Geometry.Point([-46.398372, -23.752964]).buffer(150).bounds()]
#     # [ee.Geometry.Point([-46.64488467700909, -23.641405219380577]).buffer(150).bounds()]
# )

Map.add_layer(
    ee_object=region.style(fillColor="0000", color="000F", width=5.0),
    vis_params={},
    name="First Level Administrative Units",
)

Map.center_object(region)


(
    ee.ImageCollection([ee.Image(1).clip(region.geometry())])
    .filterBounds(region)
    .map(cau_algorithms.dem())
    .aside(
        cau_map.add_layer_to_map(
            {
                "band": "dem",
                "min_max_strategy": cau_map.percentile_min_max(region.geometry()),
                "palette": [
                    "#0000FF",
                    "#000080",
                    "#00FFFF",
                    "#FFFF00",
                    "#FF0000",
                ],
            }
        ),
        Map,
    )
    .map(cau_algorithms.building_heights())
    .aside(
        cau_map.add_layer_to_map(
            {
                "band": "bh",
                "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
                "palette": [
                    "#000080",
                    "#0000FF",
                    "#00FFFF",
                    "#FFFF00",
                    "#FF0000",
                ],
            }
        ),
        Map,
    )
    .map(cau_algorithms.dsm())
    .aside(
        cau_map.add_layer_to_map(
            {
                "band": "dsm",
                "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
                "palette": [
                    "#000080",
                    "#0000FF",
                    "#00FFFF",
                    "#FFFF00",
                    "#FF0000",
                ],
            }
        ),
        Map,
    )
    .map(
        cau_algorithms.svf(
            {"dsm_band": "dsm", "num_directions": 64, "num_elevations": 64 // 4}
        )
    )
    .aside(
        cau_map.add_layer_to_map(
            {
                "band": "svf",
                "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
            }
        ),
        Map,
    )
    .map(cau_algorithms.albedo())
    .aside(
        cau_map.add_layer_to_map(
            {
                "band": "albedo",
                "min_max_strategy": cau_map.percentile_min_max(region.geometry()),
            }
        ),
        Map,
    )
    .map(cau_algorithms.ndvi())
    .aside(
        cau_map.add_layer_to_map(
            {
                "band": "ndvi",
                "min_max_strategy": cau_map.arbitrary_min_max(-1, 1),
                "palette": ["purple", "blue", "red", "yellow", "green"],
            }
        ),
        Map,
    )
    .map(cau_algorithms.ruggedness({"dem_band": "dsm"}))
    .aside(
        cau_map.add_layer_to_map(
            {
                "band": "ruggedness",
                "min_max_strategy": cau_map.percentile_min_max(region.geometry()),
                "palette": [
                    "purple",
                    "blue",
                    "green",
                    "yellow",
                    "red",
                    "black",
                ],
            }
        ),
        Map,
    )
    .map(cau_algorithms.lst())
    .aside(
        cau_map.add_layer_to_map(
            {
                "band": "lst",
                "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
                "palette": [
                    "#000004",
                    "#1b0c41",
                    "#4a0c6b",
                    "#781c6d",
                    "#a52c60",
                    "#cf4446",
                    "#ed6925",
                    "#fb9b06",
                    "#f7d13c",
                    "#fcffa4",
                ],
            }
        ),
        Map,
    )
    .mosaic()
    .clip(region)
)

Map.to_streamlit(height=600)
