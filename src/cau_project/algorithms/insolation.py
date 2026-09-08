import math

import ee

from cau_project.algorithms.config import BaseConfig


class SkyViewFactorConfig(BaseConfig, total=False):
    dsm_band: str
    num_directions: int
    num_elevations: int


type BuilderConfig = SkyViewFactorConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band = config.get("output_band", "svf")
    dsm_band: str = config.get("dsm_band", "dsm")
    num_directions: int = config.get("num_directions", 16)
    num_elevations: int = config.get("num_elevations", 8)

    def sky_view_factor(img: ee.Image):

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

        def create_weighted_shadow(index):
            i = ee.Number(index)
            idx1 = i.divide(size2).floor()
            idx2 = i.mod(size2)

            azimuth = directions.get(idx1)
            elevation = elevations.get(idx2)

            elev_rad = ee.Number(elevation).multiply(math.pi / 180)
            weight = elev_rad.cos()

            shadow = ee.Terrain.hillShadow(dsm, azimuth, elevation)

            weighted_shadow = shadow.multiply(weight).set("weight", weight)

            return weighted_shadow

        combinations = ee.List.sequence(0, total_size.subtract(1)).map(
            create_weighted_shadow
        )
        shadow_collection = ee.ImageCollection.fromImages(combinations)

        total_weight = ee.Number(shadow_collection.aggregate_sum("weight"))

        svf = shadow_collection.sum().divide(total_weight).rename(output_band)

        return img.addBands(svf)

    return sky_view_factor


svf = _builder
