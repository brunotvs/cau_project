import math
from typing import Literal

import ee

from cau_project.algorithms.config import BaseConfig


class CompactnessConfig(BaseConfig, total=False):
    height_band: str
    output_band: str
    scale: int | float
    radius: int
    radius_units: Literal["meters", "pixels"]


type BuilderConfig = CompactnessConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "compactness")
    height_band: str = config.get("height_band", "bh")
    scale: int | float = config.get("scale", 1.0)
    radius: int = config.get("radius", 5)
    radius_units: str = config.get("radius_units", "meters")

    def compactness(img: ee.Image) -> ee.Image:
        heights: ee.Image = img.select(height_band).unmask(0)

        # 1. Building footprints and horizontal surface area
        is_building = heights.gt(0)
        pixel_area = ee.Image.pixelArea().multiply(is_building)

        # 2. Local volume: sum(height * pixel_area)
        pixel_volume = heights.multiply(pixel_area)

        # 3. Façade / vertical surface area derived from slope gradients
        # Gradient magnitudes represent height difference per horizontal unit
        gradients = heights.gradient()
        grad_x = gradients.select("x")
        grad_y = gradients.select("y")
        facade_area_density = grad_x.hypot(grad_y).multiply(is_building)
        facade_area = facade_area_density.multiply(scale)

        # 4. Total exterior envelope area (roofs + exterior vertical facades)
        total_surface_area = pixel_area.add(facade_area)

        # 5. Aggregate metrics within a local neighborhood kernel
        kernel = ee.Kernel.circle(radius=radius, units=radius_units)

        neighborhood_volume = pixel_volume.reduceNeighborhood(
            reducer=ee.Reducer.sum(),
            kernel=kernel,
        )

        neighborhood_surface = total_surface_area.reduceNeighborhood(
            reducer=ee.Reducer.sum(),
            kernel=kernel,
        )

        # 6. Volumetric Compactness: (36 * pi * Volume^2)^(1/3) / Total_Surface_Area
        # Spherical normalized isoperimetric ratio (ranges between 0 and 1)
        factor = 36.0 * math.pi
        compactness = (
            neighborhood_volume.pow(2)
            .multiply(factor)
            .pow(1.0 / 3.0)
            .divide(neighborhood_surface)
            .where(neighborhood_surface.lte(0), 0)
            .rename(output_band)
        )

        return img.addBands(compactness)

    return compactness


compactness = _builder
