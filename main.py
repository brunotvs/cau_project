import ee
import geemap.foliumap as geemap
import streamlit as st


st.set_page_config(layout="wide")
st.title("Interactive Earth Engine Dashboard")

ee.Initialize(project="earth-cau")


Map = geemap.Map()

region = (
    ee.FeatureCollection("FAO/GAUL/2015/level2")
    .filter(ee.Filter.eq("ADM1_NAME", "Sao Paulo"))
    .filter(ee.Filter.eq("ADM2_NAME", "Rio Grande Da Serra"))
)

Map.add_layer(
    ee_object=region.style(fillColor="b5ffb4", color="00909F", width=2.0),
    vis_params={},
    name="First Level Administrative Units",
)

Map.center_object(region)

heights: ee.Image = (
    ee.ImageCollection("GOOGLE/Research/open-buildings-temporal/v1")
    .filterBounds(region)
    .filterDate("2023-01-01", "2023-12-31")
    .select("building_height")
    .mosaic()
    .clip(region)
)

height_extrema = heights.reduceRegion(
    reducer=ee.Reducer.minMax(),
    geometry=region.geometry(),
    scale=30,
    maxPixels=int(1e9),
)

Map.add_layer(
    ee_object=heights,
    vis_params={
        "min": 0,
        "max": height_extrema.get("building_height_max"),
        "palette": [
            "#000080",
            "#0000FF",
            "#00FFFF",
            "#FFFF00",
            "#FF0000",
        ],
    },
    name="Building Heights (m)",
)

dem = (
    ee.Image("USGS/SRTMGL1_003")
    .clip(region)
    .resample("bicubic")
    .reproject(crs="EPSG:4326", scale=2)
)

dem_extrema = dem.reduceRegion(
    reducer=ee.Reducer.minMax(),
    geometry=region.geometry(),
    scale=30,
    maxPixels=int(1e9),
)

Map.add_layer(
    ee_object=dem,
    vis_params={
        "min": dem_extrema.get("elevation_min"),
        "max": dem_extrema.get("elevation_max"),
        "palette": [
            "#000080",
            "#0000FF",
            "#00FFFF",
            "#FFFF00",
            "#FF0000",
        ],
    },
    name="Digital elevation model",
)

dsm: ee.Image = dem.select("elevation").add(heights)

dsm_extrema = dsm.reduceRegion(
    reducer=ee.Reducer.minMax(),
    geometry=region.geometry(),
    scale=30,
    maxPixels=int(1e9),
)

Map.add_layer(
    ee_object=dem,
    vis_params={
        "min": dsm_extrema.get("elevation_min"),
        "max": dsm_extrema.get("elevation_max"),
        "palette": [
            "#000080",
            "#0000FF",
            "#00FFFF",
            "#FFFF00",
            "#FF0000",
        ],
    },
    name="Digital surface model",
)


num_directions = 16
num_elevations = 8
directions = ee.List.sequence(0, num_directions - 1).map(
    lambda value: ee.Number(value).multiply(360 / num_directions)
)

elevations = ee.List.sequence(0, num_elevations).map(
    lambda value: ee.Number(value).multiply(90 / num_elevations)
)

size1 = directions.size()
size2 = elevations.size()
total_size = size1.multiply(size2)


def create_pair(index):
    i = ee.Number(index)
    idx1 = i.divide(size2).floor()
    idx2 = i.mod(size2)
    return ee.List([directions.get(idx1), elevations.get(idx2)])


combinations = ee.List.sequence(0, total_size.subtract(1)).map(create_pair)

svf = (
    ee.ImageCollection.fromImages(
        combinations.map(
            lambda angles: (
                ee.Terrain.hillShadow(
                    dsm,
                    ee.List(angles).get(0),
                    ee.List(angles).get(1),
                    neighborhoodSize=200,
                    hysteresis=True,
                )
                .Not()
                .Not()
            )
        )
    )
    .sum()
    .clip(region)
    .divide(total_size)
)

svf_extrema = svf.reduceRegion(
    reducer=ee.Reducer.minMax(),
    geometry=region.geometry(),
    scale=30,
    maxPixels=int(1e9),
    tileScale=4,
)

Map.add_layer(
    ee_object=svf,
    vis_params={
        "min": svf_extrema.get("shadow_min"),
        "max": svf_extrema.get("shadow_max"),
    },
    name="SVF",
)

ndvi: ee.Image = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(region)
    .filterMetadata("CLOUDY_PIXEL_PERCENTAGE", "less_than", 20)
    .filterDate("2025-01-01", "2025-12-31")
    .mosaic()
    .clip(region)
    .normalizedDifference(["B8", "B4"])
)


Map.add_layer(
    ee_object=ndvi,
    vis_params={
        "min": -1,
        "max": 1,
        "palette": ["blue", "blue", "red", "yellow", "green"],
    },
    name="NDVI",
)

Map.to_streamlit(height=600)
