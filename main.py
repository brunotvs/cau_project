import json
import os
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import HTTPError

import ee
import geemap.foliumap as geemap
import numpy as np
import streamlit as st
from osgeo import gdal, osr

st.set_page_config(layout="wide")
st.title("Interactive Earth Engine Dashboard")

ee.Initialize(project="earth-cau")

Map = geemap.Map()

region = (
    ee.FeatureCollection("FAO/GAUL/2015/level2")
    .filter(ee.Filter.eq("ADM1_NAME", "Sao Paulo"))
    .filter(ee.Filter.eq("ADM2_NAME", "Sao Paulo"))
    # .filter(ee.Filter.eq("ADM1_NAME", "Minas Gerais"))
    # .filter(ee.Filter.eq("ADM2_NAME", "Santa Cruz De Minas"))
)

Map.add_layer(region.bounds())

bounds = region.bounds().coordinates().getInfo()


def calculate_utm_epsg(lat, lon):
    is_northern = lat >= 0

    zone_number = int((lon + 180) / 6) + 1

    # 3. Handle special UTM zone exceptions (e.g., Norway/Svalbard) if needed
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone_number = 32

    if is_northern:
        epsg_code = 32600 + zone_number
    else:
        epsg_code = 32700 + zone_number

    return epsg_code


def fix_sheet(name):
    fixes = {
        "25S48_": "24S48_",
        "24S465": "23S465",
    }

    return fixes.get(name) or name


def assure_topodata(sheet):
    output_dir = Path(".topodata")
    output_dir.mkdir(parents=True, exist_ok=True)
    tif_path = output_dir / f"{sheet}.tif"
    if tif_path.is_file():
        return sheet

    try:
        url = f"http://www.dsr.inpe.br/topodata/data/geotiff/{sheet}.zip"

        local_filename = output_dir / f"{sheet}.zip"

        urllib.request.urlretrieve(url, local_filename)

        with zipfile.ZipFile(local_filename, "r") as zip_ref:
            zip_ref.extractall(output_dir)

            os.remove(local_filename)

        with gdal.Open(tif_path, 1) as dataset:
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(4326)
            dataset.SetSpatialRef(srs)

    except HTTPError:
        return

    except Exception as e:
        print(f"failed to acquire topodata layer named {sheet}")
        print(e, file=sys.stderr)
        return


def get_topodata(bounds, layers: dict[str, str] = {"ZN": "altitude"}):
    min_lon = -36
    lon_mult = 1.5

    points = np.array(bounds[0])
    lon_1, la_1 = points.min(axis=0)
    lon_2, la_2 = points.max(axis=0)
    print(la_1, la_2, lon_1, lon_2)

    la_1 = int(abs(la_1) // 1) * (la_1 / abs(la_1))
    la_2 = int(abs(la_2) // 1) * (la_2 / abs(la_2))

    lon_1 = ((abs(lon_1 - min_lon) // lon_mult + 1) * lon_mult) * (
        lon_1 / abs(lon_1)
    ) + min_lon

    lon_2 = ((abs(lon_2 - min_lon) // lon_mult + 1) * lon_mult) * (
        lon_2 / abs(lon_2)
    ) + min_lon

    def format_lon(lon):
        if lon % 10 == 0:
            lon = lon // 10

        return str(lon).ljust(3, "_")

    las = [la for la in range(int(la_1), int(la_2) + 1, 1)]
    lons = [lon for lon in range(10 * int(lon_1), 10 * int(lon_2), 15)]
    sheets = {
        layer: {
            fix_sheet(f"{abs(la):.0f}S{format_lon(abs(lon))}") + f"{key}"
            for la in las
            for lon in lons
        }
        for key, layer in layers.items()
    }
    print(sheets)

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = {}
        for layer, values in sheets.items():
            results[layer] = filter(None, executor.map(assure_topodata, values))

    asset = {
        "name": "projects/earth-cau/assets/topodata",
        "tilesets": [
            {
                "id": layer,
                "sources": [
                    {"uris": [f"gs://earth-cau/{f}.tif"]} for f in layer_sheets
                ],
            }
            for layer, layer_sheets in results.items()
        ],
    }

    with open("./.topodata/topodata-manifest.json", "w") as manifest:
        print(json.dumps(asset, indent=2), file=manifest)


get_topodata(bounds)


Map.center_object(region)

Map.add_layer(
    ee_object=region.style(fillColor="b5ffb4", color="00909F", width=2.0),
    vis_params={},
    name="First Level Administrative Units",
)


heights: ee.Image = (
    ee.ImageCollection("GOOGLE/Research/open-buildings-temporal/v1")
    .filterBounds(region)
    .select("building_height")
    .mosaic()
    .clip(region)
)

max_height = (
    heights.reduceRegion(
        reducer=ee.Reducer.max(),
        geometry=region.geometry(),
        scale=30,
        maxPixels=int(1e9),
    )
    .get("building_height")
    .getInfo()
)


if max_height is None:
    max_height = 30

Map.add_layer(
    ee_object=heights,
    vis_params={
        "min": 0,
        "max": max_height,
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

buildings_coordinates = (
    ee.FeatureCollection("GOOGLE/Research/open-buildings/v3/polygons")
    .filterBounds(region)
    .geometry()
    .coordinates()
)

Map.to_streamlit(height=600)
