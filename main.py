import ee
import geemap.foliumap as geemap
import streamlit as st

st.title("Interactive Earth Engine Dashboard")

ee.Initialize(project="earth-cau")

Map = geemap.Map()

dataset = (
    ee.FeatureCollection("FAO/GAUL/2015/level2")
    .filter(ee.Filter.eq("ADM1_NAME", "Sao Paulo"))
    .filter(ee.Filter.eq("ADM2_NAME", "Rio Grande Da Serra"))
)


Map.add_layer(
    dataset.style(fillColor="b5ffb4", color="00909F", width=1.0),
    {},
    "First Level Administrative Units",
)


Map.center_object(dataset)

Map.to_streamlit(height=600)
