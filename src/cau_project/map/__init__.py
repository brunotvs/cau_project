from collections.abc import Callable
from typing import Any, NotRequired, Required, TypedDict

import ee
import geemap

MinMaxStrategy = Callable[[ee.ImageCollection, list[str]], dict[str, Any]]


def arbitrary_min_max(min_val: float, max_val: float) -> MinMaxStrategy:
    def strategy(img: ee.ImageCollection, bands: list[str]) -> dict[str, Any]:
        return {"min": min_val, "max": max_val}

    return strategy


def absolute_min_max(region: ee.Geometry, scale: int = 1) -> MinMaxStrategy:
    """Strategy: Computes the absolute min and max of the image using EE reducers."""

    def strategy(img: ee.ImageCollection, bands: list[str]) -> dict[str, Any]:
        stats = img.select(bands).reduce(
            reducer=ee.Reducer.minMax(),
            parallelScale=scale,
        )

        mins = [
            stats.select(f"{b}_min")
            .reduceRegion(
                reducer=ee.Reducer.min(),
                geometry=region,
                bestEffort=True,
                scale=30,
                tileScale=4,
            )
            .get(f"{b}_min")
            for b in bands
        ]
        maxes = [
            stats.select(f"{b}_max")
            .reduceRegion(
                reducer=ee.Reducer.max(),
                geometry=region,
                bestEffort=True,
                scale=30,
                tileScale=4,
            )
            .get(f"{b}_max")
            for b in bands
        ]

        return {"min": mins, "max": maxes}

    return strategy


def percentile_min_max(
    region: ee.Geometry, p_min: int = 2, p_max: int = 98, scale: int = 1
) -> MinMaxStrategy:

    def strategy(img: ee.ImageCollection, bands: list[str]) -> dict[str, Any]:
        stats = img.select(bands).reduce(
            reducer=ee.Reducer.percentile([p_min, p_max]),
            parallelScale=scale,
        )

        mins = [
            stats.select(f"{b}_p{p_min}")
            .reduceRegion(
                reducer=ee.Reducer.min(),
                geometry=region,
                bestEffort=True,
                scale=30,
                tileScale=4,
            )
            .get(f"{b}_p{p_min}")
            for b in bands
        ]

        maxes = [
            stats.select(f"{b}_p{p_max}")
            .reduceRegion(
                reducer=ee.Reducer.max(),
                geometry=region,
                bestEffort=True,
                scale=30,
                tileScale=4,
            )
            .get(f"{b}_p{p_max}")
            for b in bands
        ]

        return {"min": mins, "max": maxes}

    return strategy


class BaseLayerConfig(TypedDict, total=False):
    min_max_strategy: Required[MinMaxStrategy]
    opacity: float
    name: str


class MultiBandLayerConfig(BaseLayerConfig):
    bands: list[str]


class SingleBandLayerConfig(BaseLayerConfig):
    band: str
    palette: NotRequired[list[str]]


type LayerConfig = MultiBandLayerConfig | SingleBandLayerConfig


def add_layer_to_map(layer_config: LayerConfig):
    """The Context: Executes the strategy and adds the layer to the map."""

    min_max_strategy = layer_config.get("min_max_strategy", None)
    bands = layer_config.get("bands", [layer_config.get("band")])
    palette = layer_config.get("palette")
    layer_name = layer_config.get("name", f"Layer ({', '.join(bands)})")

    def callback(img: ee.ImageCollection, map_obj: geemap.Map):

        min_max_params = min_max_strategy(img, bands)

        vis_params = {"bands": bands, **min_max_params}

        if palette is not None:
            vis_params["palette"] = palette

        map_obj.addLayer(
            img.map(lambda i: i.clip(img.geometry())), vis_params, layer_name
        )

    return callback
