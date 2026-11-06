import json

import ee
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .cache import CACHE_DIR, ee_hash


def correlation_visualization(
    correlation_dict: dict[str, dict[str, float]],
    figsize: tuple[int, int] = (12, 10),
    rename_map: dict[str, str] | None = None,
):

    rename_map = rename_map or {}
    correlation_dict = {
        rename_map.get(r, r).upper(): {
            rename_map.get(c, c).upper(): v for c, v in cols.items()
        }
        for r, cols in correlation_dict.items()
    }

    corr_df = pd.DataFrame(correlation_dict).round(2)
    _, ax = plt.subplots(figsize=figsize)
    mask = np.triu(np.ones_like(corr_df, dtype=bool), k=1)
    sns.heatmap(
        corr_df,
        mask=mask,
        annot=True,
        fmt=".2f",
        annot_kws={"size": 9},
        cmap="coolwarm_r",
        vmin=-1,
        vmax=1,
        center=0,
        square=True,
        cbar=False,
        ax=ax,
    )
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return plt


def sampled_correlation(img, region, scale=5, factor=0.1):
    img = ee.Image(img)
    geom = region.geometry()

    cov = ee.Array(
        img.toArray()
        .sample(
            region=geom,
            scale=scale,
            # factor=factor,
            numPixels=50000,
            tileScale=16,
            geometries=False,
        )
        .reduceColumns(
            reducer=ee.Reducer.covariance(),
            selectors=["array"],
        )
        .get("Covariance")
    )
    return _get_correlation_dict(cov, img)


def correlation(img, region, scale=5):

    img = ee.Image(img)

    cov = ee.Array(
        img.toArray()
        .reduceRegion(
            reducer=ee.Reducer.covariance(),
            geometry=region.geometry(),
            scale=scale,
            tileScale=16,
            bestEffort=True,
        )
        .get("array")
    )
    return _get_correlation_dict(cov, img)


def _get_correlation_dict(cov, img) -> dict[str, dict[str, float]]:
    bands = img.bandNames()
    n = bands.size()
    std_list = cov.matrixDiagonal().sqrt().project([0]).toList()

    valid_idx = (
        ee.List.sequence(0, n.subtract(1))
        .map(lambda i: ee.Algorithms.If(ee.Number(std_list.get(i)).gt(1e-9), i, None))
        .removeAll([None])
    )

    valid_bands = valid_idx.map(lambda i: bands.get(i))

    cov_rows = cov.toList()

    def pick(i):
        row = ee.List(cov_rows.get(ee.Number(i)))
        return valid_idx.map(lambda j: row.get(j))

    cov_f = ee.Array(valid_idx.map(pick))

    std_f = cov_f.matrixDiagonal().sqrt()
    corr = cov_f.divide(std_f.matrixMultiply(std_f.transpose()))

    rows = corr.toList().map(
        lambda row: ee.Dictionary.fromLists(valid_bands, ee.List(row))
    )

    ee_object = ee.Dictionary.fromLists(valid_bands, rows)

    hash = ee_hash(ee_object)

    path = CACHE_DIR / hash

    if not path.is_file():
        content = ee_object.getInfo() or {}

        with open(path, "w", encoding="utf-8") as f:
            json.dump(content, f)

        return content
    else:
        with open(path, "r", encoding="utf-8") as f:
            content = json.load(f)

        return content
