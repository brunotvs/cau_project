import ee
import geemap.foliumap as geemap
import streamlit as st

import cau_project.algorithms as cau_algorithms
import cau_project.indicators as cau_indicators
import cau_project.map as cau_map
import cau_project.palettes as cau_palettes
import cau_project.study_areas as cau_areas

ee.Initialize(project="earth-cau")


st.set_page_config(layout="wide")
st.title("Interactive Earth Engine Dashboard")


Map = geemap.Map(basemap="HYBRID")


region = (
    ee.FeatureCollection("FAO/GAUL/2025/level2")
    .filter(ee.Filter.eq("GAUL1_NAME", "São Paulo"))
    .filter(ee.Filter.eq("GAUL2_NAME", "Teodoro Sampaio"))
)

# region = ee.FeatureCollection(cau_areas.jabaquara)


# grid = region.geometry().coveringGrid(proj=ee.Projection("EPSG:31983"), scale=100)
#
# Map.add_layer(
#     ee_object=grid.style(fillColor="0000", color="000F", width=5.0),
#     vis_params={},
#     name="Grid",
# )

Map.center_object(region)

day = ee.Date("2023-01-01T16:00:00-03:00")

y, d, m = cau_indicators.indicators(region.geometry(), day, 2**4, 15, "minute", 100)

y.aside(
    cau_map.add_layer_to_map(
        {
            "band": "emissivity",
            "min_max_strategy": cau_map.percentile_min_max(region.geometry(), 5, 95),
        }
    ),
    Map,
).aside(
    cau_map.add_layer_to_map(
        {
            "band": "albedo",
            "min_max_strategy": cau_map.percentile_min_max(region.geometry(), 5, 95),
        }
    ),
    Map,
).aside(
    cau_map.add_layer_to_map(
        {
            "band": "svf",
            "min_max_strategy": cau_map.arbitrary_min_max(0, 1),
        }
    ),
    Map,
)

d.aside(
    cau_map.add_layer_to_map(
        {
            "band": "lst",
            "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
            "palette": cau_palettes.temperature,
        }
    ),
    Map,
).aside(
    cau_map.add_layer_to_map(
        {
            "band": "radiation",
            "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
            "palette": cau_palettes.qgis_ylorrd,
        }
    ),
    Map,
)


y.aside(
    lambda img: print(
        ee.Image(img.select("emissivity"))
        .reduceRegion(
            reducer=ee.Reducer.minMax(),
            geometry=region.geometry(),
            scale=5,
            tileScale=16,
            bestEffort=True,
        )
        .getInfo()
    )
)

Map.add_layer(
    ee_object=region.style(fillColor="0000", color="000F", width=5.0),
    vis_params={},
    name="First Level Administrative Units",
)
Map.to_streamlit(height=600)
