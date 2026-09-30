import math

import ee

from cau_project.algorithms.config import BaseConfig


class AreaConfig(BaseConfig, total=False):
    dsm_band: str


type BuilderConfig = AreaConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "area")

    def area(img: ee.Image) -> ee.Image:
        area = (
            ee.Image.pixelArea()
            .divide(ee.Terrain.slope(img.select("dsm")).multiply(math.pi / 180).cos())
            .rename(output_band)
        )

        return img.addBands(area)

    return area


area = _builder

__all__ = ["area"]
