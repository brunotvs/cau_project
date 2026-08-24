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


(
    ee.ImageCollection([ee.Image(1).clip(region.geometry())])
    .filterBounds(region)
    .map(cau_algorithms.dem())
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "dem",
    #             "min_max_strategy": cau_map.percentile_min_max(region.geometry()),
    #             "palette": [
    #                 "#0000FF",
    #                 "#000080",
    #                 "#00FFFF",
    #                 "#FFFF00",
    #                 "#FF0000",
    #             ],
    #         }
    #     ),
    #     Map,
    # )
    .map(cau_algorithms.building_heights())
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "bh",
    #             "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #             "palette": [
    #                 "#000080",
    #                 "#0000FF",
    #                 "#00FFFF",
    #                 "#FFFF00",
    #                 "#FF0000",
    #             ],
    #         }
    #     ),
    #     Map,
    # )
    .map(cau_algorithms.dsm())
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "dsm",
    #             "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #             "palette": [
    #                 "#000080",
    #                 "#0000FF",
    #                 "#00FFFF",
    #                 "#FFFF00",
    #                 "#FF0000",
    #             ],
    #         }
    #     ),
    #     Map,
    # )
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
    .mosaic()
    .clip(region)
)

Map.to_streamlit(height=600)
