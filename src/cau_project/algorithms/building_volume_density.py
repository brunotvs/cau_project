from typing import Literal

import ee

from cau_project.algorithms.config import BaseConfig


class BuildingVolumeDensityConfig(BaseConfig, total=False):
    height_band: str
    radius: int
    radius_units: Literal["meters", "pixels"]


type BuilderConfig = BuildingVolumeDensityConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "bvd")
    height_band: str = config.get("height_band", "bh")
    radius: int = config.get("radius", 100)
    radius_units: str = config.get("radius_units", "meters")

    def building_volume_density(img: ee.Image) -> ee.Image:
        kernel = ee.Kernel.circle(radius=radius, units=radius_units)

        heights: ee.Image = img.select(height_band).unmask(0)

        is_building = heights.gt(0)

        land_area = ee.Image.pixelArea().reduceNeighborhood(
            reducer=ee.Reducer.sum(),
            kernel=kernel,
        )

        building_volume = (
            land_area.multiply(is_building)
            .multiply(heights)
            .reduceNeighborhood(reducer=ee.Reducer.sum(), kernel=kernel)
        )

        bvd = building_volume.divide(land_area).rename(output_band)

        return img.addBands(bvd)

    return building_volume_density


building_volume_density = _builder
