import math
from typing import Required

import ee

from .config import BaseConfig


class HillshadeConfig(BaseConfig, total=False):
    dem_band: str
    bh_band: str
    azimuth: Required[float | ee.Number]
    zenith: Required[float | ee.Number]


type BuilderConfig = HillshadeConfig


def _builder(
    user_config: BuilderConfig | None = None,
):

    config: BuilderConfig = user_config or {"azimuth": 45, "zenith": 270}
    shade_band = config.get("output_band", "hillshade")
    dem_band: str = config.get("dem_band", "dem")
    bh_band: str = config.get("bh_band", "bh")
    azimuth: ee.Number = ee.Number(config.get("azimuth"))
    zenith: ee.Number = ee.Number(config.get("zenith"))

    def hillshade(img: ee.Image):
        bh = img.select(bh_band).unmask(0)
        dem = img.select(dem_band)

        dsm = bh.unmask(0).add(dem)

        slope = ee.Terrain.slope(dsm).multiply(math.pi / 180)
        aspect = ee.Terrain.aspect(dsm).multiply(math.pi / 180)

        alt = ee.Number(90).subtract(zenith).multiply(math.pi / 180)
        az = ee.Number(azimuth).multiply(math.pi / 180)

        shade = (
            slope.cos()
            .multiply(alt.sin())
            .add(slope.sin().multiply(alt.cos()).multiply(aspect.subtract(az).cos()))
            .max(0)
        ).rename(shade_band)

        return img.addBands(shade)

    return hillshade


hillshade = _builder

__all__ = [
    "hillshade",
]
