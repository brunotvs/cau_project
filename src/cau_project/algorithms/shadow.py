import math

import ee

from cau_project.algorithms.config import BaseConfig


class ShadowConfig(BaseConfig, total=False):
    dsm_band: str
    num_directions: int
    num_elevations: int


type BuilderConfig = ShadowConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band = config.get("output_band", "shadow")
    dsm_band: str = config.get("dsm_band", "dsm")
    num_directions: int = 320
    num_elevations: int = 320 // 4

    def shadow(img: ee.Image):

        dsm = img.select(dsm_band)

        directions = ee.List.sequence(0, num_directions - 1).map(
            lambda value: ee.Number(value).multiply(360 / num_directions)
        )

        elevations = ee.List.sequence(0, num_elevations - 1).map(
            lambda value: (
                ee.Number(value).multiply(90 / (num_elevations - 1))
                if num_elevations > 1
                else 90
            )
        )

        size1 = directions.size()
        size2 = elevations.size()
        total_size = size1.multiply(size2)

        def create_shadow(index):
            i = ee.Number(index)
            idx1 = i.divide(size2).floor()
            idx2 = i.mod(size2)

            azimuth = directions.get(idx1)
            elevation = elevations.get(idx2)

            return (
                ee.Terrain.hillShadow(dsm, azimuth, elevation)
                .set("azimuth", azimuth)
                .set("elevation", elevation)
            )

        combinations = ee.List.sequence(0, total_size.subtract(1)).map(create_shadow)
        shadow_collection = ee.ImageCollection.fromImages(combinations)

        total_weight = ee.Number(shadow_collection.aggregate_sum("weight"))

        svf = shadow_collection.sum().divide(total_weight).rename(output_band)

        return img.addBands(svf)

    return shadow


shadow = _builder
