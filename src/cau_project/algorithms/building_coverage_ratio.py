from typing import Literal

import ee

from cau_project.algorithms.config import BaseConfig


class BuildingCoverageRatioConfig(BaseConfig, total=False):
    height_band: str
    radius: int
    radius_units: Literal["meters", "pixels"]
    scale: int


type BuilderConfig = BuildingCoverageRatioConfig


def _builder(user_config: BuilderConfig | None = None):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "bcr")
    height_band: str = config.get("height_band", "bh")
    radius: int = config.get("radius", 50)
    radius_units: Literal["meters", "pixels"] = config.get("radius_units", "meters")
    scale: int | None = config.get("scale")

    def building_coverage_ratio(img: ee.Image) -> ee.Image:
        is_building = img.select(height_band).unmask(0).gt(0)

        if scale is not None:
            is_building = is_building.reduceResolution(
                reducer=ee.Reducer.mean(), maxPixels=1024
            ).reproject(is_building.projection().atScale(scale))

        bcr = is_building.focalMean(
            radius=radius, kernelType="circle", units=radius_units
        ).rename(output_band)

        return img.addBands(bcr)

    return building_coverage_ratio


building_coverage_ratio = _builder
