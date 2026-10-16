import ee
import geemap.foliumap as geemap
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

import cau_project.algorithms as cau_algorithms
import cau_project.study_areas as cau_areas

ee.Initialize(project="earth-cau")


def visualize_correlation(
    correlation_dict: dict[str, dict[str, float]],
    rename_map: dict[str, str] | None = None,
):

    rename_map = rename_map or {}
    correlation_dict = {
        rename_map.get(r, r): {rename_map.get(c, c): v for c, v in cols.items()}
        for r, cols in correlation_dict.items()
    }

    corr_df = pd.DataFrame(correlation_dict).round(2)
    _, ax = plt.subplots(figsize=(8, 6))
    mask = np.triu(np.ones_like(corr_df, dtype=bool), k=1)
    sns.heatmap(
        corr_df,
        mask=mask,
        annot=True,
        cbar=False,
        fmt=".2f",
        cmap="coolwarm_r",
        vmin=-1,
        vmax=1,
        square=True,
        ax=ax,
    )
    plt.tight_layout()
    plt.show()


def correlation(img):

    img = ee.Image(img)
    bands = img.bandNames()
    n = bands.size()

    cov = ee.Array(
        img.toArray()
        .reduceRegion(
            reducer=ee.Reducer.covariance(),
            geometry=region.geometry(),
            scale=5,
            bestEffort=True,
        )
        .get("array")
    )

    std_list = cov.matrixDiagonal().sqrt().project([0]).toList()

    valid_idx = (
        ee.List.sequence(0, n.subtract(1))
        .map(lambda i: ee.Algorithms.If(ee.Number(std_list.get(i)).gt(1e-9), i, None))
        .removeAll([None])
    )

    valid_bands = valid_idx.map(lambda i: bands.get(i))

    cov_rows = cov.toList()  # fora do pick, para não recriar a cada chamada

    def pick(i):
        row = ee.List(cov_rows.get(ee.Number(i)))
        return valid_idx.map(lambda j: row.get(j))

    cov_f = ee.Array(valid_idx.map(pick))

    std_f = cov_f.matrixDiagonal().sqrt()
    corr = cov_f.divide(std_f.matrixMultiply(std_f.transpose()))

    rows = corr.toList().map(
        lambda row: ee.Dictionary.fromLists(valid_bands, ee.List(row))
    )
    return ee.Dictionary.fromLists(valid_bands, rows)


arr = ee.Array(
    [
        [21.068866546950073, 6.469278168301863, -14.599588378649118],
        [6.469278168301863, 674.143896135019, 667.6746179667889],
        [-14.599588378649118, 667.6746179667889, 682.2742063455033],
    ]
)

stddev = arr.matrixDiagonal().sqrt()
# print(stddev.getInfo())

prods = stddev.matrixMultiply(stddev.transpose())
# print(prods.getInfo())


corr = arr.divide(prods)

st.set_page_config(layout="wide")
st.title("Interactive Earth Engine Dashboard")


Map = geemap.Map(basemap="HYBRID")


region = (
    ee.FeatureCollection("FAO/GAUL/2025/level2")
    .filter(ee.Filter.eq("GAUL1_NAME", "São Paulo"))
    .filter(ee.Filter.eq("GAUL2_NAME", "Rio Grande Da Serra"))
)

region = ee.FeatureCollection(cau_areas.jabaquara)


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


num_directions = 12
num_elevations = num_directions // 4
(
    ee.ImageCollection(dates_list.map(create_empty_image))
    .map(cau_algorithms.lst())
    .map(cau_algorithms.dem())
    .map(cau_algorithms.building_height())
    .map(cau_algorithms.dsm())
    .map(cau_algorithms.walls())
    .map(
        cau_algorithms.svf(
            {"num_directions": num_directions, "num_elevations": num_elevations}
        )
    )
    .map(cau_algorithms.urban_area())
    .map(cau_algorithms.heat_island_intensity({"geometry": region.geometry()}))
    .filterBounds(region)
    .map(lambda img: img.clip(region))
    .map(lambda img: img.select(img.bandNames().remove("constant")))
    .first()
    .aside(
        lambda img: visualize_correlation(
            correlation(img).getInfo() or {}, {"bh": "building heights"}
        )
    )
)


Map.to_streamlit(height=600)
