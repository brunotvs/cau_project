from typing import Literal

import ee

from cau_project.algorithms.config import BaseConfig


class RuggednessConfig(BaseConfig, total=False):
    height_band: str
    radius: int
    radius_units: Literal["meters", "pixels"]


type BuilderConfig = RuggednessConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band = config.get("output_band", "ruggedness")
    height_band = config.get("height_band", "dem")
    radius = config.get("radius", 1)
    radius_units = config.get("radius_units", "pixels")

    empty_image = ee.Image()

    # Riley et al., 1999
    def ruggedness(img: ee.Image = empty_image):
        kernel = ee.Kernel.square(radius=radius, units=radius_units)

        heights: ee.Image = img.select(height_band)
        sum_dem = heights.reduceNeighborhood(reducer=ee.Reducer.sum(), kernel=kernel)

        sum_dem_sq = heights.pow(2).reduceNeighborhood(
            reducer=ee.Reducer.sum(), kernel=kernel
        )

        valid_pixel_count = heights.mask().reduceNeighborhood(
            reducer=ee.Reducer.sum(), kernel=kernel
        )

        rugg = (
            sum_dem_sq.subtract(heights.multiply(sum_dem).multiply(2))
            .add(heights.pow(2).multiply(valid_pixel_count))
            .max(0)
            .sqrt()
            .rename(output_band)
        )

        return img.addBands(rugg)

    return ruggedness


ruggedness = _builder
