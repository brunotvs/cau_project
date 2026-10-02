from typing import Literal

import ee

from cau_project.algorithms.config import BaseConfig


class BuildingCoverageRationConfig(BaseConfig, total=False):
    height_band: str
    radius: int
    radius_units: Literal["meters", "pixels"]


type BuilderConfig = BuildingCoverageRationConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "bcr")
    height_band: str = config.get("height_band", "bh")
    radius: int = config.get("radius", 50)
    radius_units: str = config.get("radius_units", "meters")

    def building_coverage_ration(img: ee.Image) -> ee.Image:

        kernel = ee.Kernel.circle(radius=radius, units=radius_units, normalize=True)

        heights: ee.Image = img.select(height_band).unmask(0)

        is_building = heights.gt(0)
        land_area = ee.Image.pixelArea().convolve(
            kernel=kernel,
        )

        building_area = land_area.multiply(is_building).convolve(
            kernel=kernel,
        )

        bcr = building_area.divide(land_area).rename(output_band)

        return img.addBands(bcr)

    return building_coverage_ration


building_coverage_ratio = _builder
