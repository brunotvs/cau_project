from typing import Literal

import ee

from cau_project.algorithms.config import BaseConfig


class AveragedBuildingHeightConfig(BaseConfig, total=False):
    height_band: str
    radius: int
    radius_units: Literal["meters", "pixels"]


type BuilderConfig = AveragedBuildingHeightConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "abh")
    height_band: str = config.get("height_band", "bh")
    radius: int = config.get("radius", 100)
    radius_units: str = config.get("radius_units", "meters")

    def averaged_building_height(img: ee.Image) -> ee.Image:
        kernel = ee.Kernel.circle(radius=radius, units=radius_units)

        heights: ee.Image = img.select(height_band).unmask(0)

        is_building = heights.gt(0)
        land_area = ee.Image.pixelArea()

        building_area = land_area.multiply(is_building).reduceNeighborhood(
            reducer=ee.Reducer.sum(),
            kernel=kernel,
        )

        building_volume = building_area.multiply(heights).reduceNeighborhood(
            reducer=ee.Reducer.sum(), kernel=kernel
        )

        abh = building_volume.divide(building_area).rename(output_band)

        return img.addBands(abh)

    return averaged_building_height


averaged_building_height = _builder
