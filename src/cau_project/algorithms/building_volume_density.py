from typing import Literal

import ee

from cau_project.algorithms.config import BaseConfig


class BuildingVolumeDensityConfig(BaseConfig, total=False):
    height_band: str
    radius: int
    radius_units: Literal["meters", "pixels"]
    scale: int | None


type BuilderConfig = BuildingVolumeDensityConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "bvd")
    height_band: str = config.get("height_band", "bh")
    radius: int = config.get("radius", 50)
    radius_units: Literal["meters", "pixels"] = config.get("radius_units", "meters")
    scale: int | None = config.get("scale")

    def building_volume_density(img: ee.Image) -> ee.Image:
        heights = img.select(height_band).unmask(0).max(0)

        if scale is not None:
            heights = heights.reduceResolution(
                reducer=ee.Reducer.mean(), maxPixels=1024
            ).reproject(heights.projection().atScale(scale))

        bvd = heights.focalMean(
            radius=radius, kernelType="circle", units=radius_units
        ).rename(output_band)

        return img.addBands(bvd)

    return building_volume_density


building_volume_density = _builder
