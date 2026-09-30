import math

import ee

from .config import BaseConfig


class DirectIrradianceConfig(BaseConfig, total=False):
    dsm_band: str
    ghi_band: str
    albedo_band: str


type BuilderConfig = DirectIrradianceConfig


def _builder(
    user_config: BuilderConfig | None = None,
):

    config: BuilderConfig = user_config or {}
    reflected_band: str = config.get("output_band", "reflected_irradiance")
    dsm_band: str = config.get("dsm_band", "dsm")
    ghi_band: str = config.get("ghi_band", "ghi")
    albedo_band: str = config.get("albedo_band", "albedo")

    def reflected_irradiance(img: ee.Image):
        dsm: ee.Image = img.select(dsm_band)
        ghi: ee.Image = img.select(ghi_band)
        albedo: ee.Image = img.select(albedo_band)

        slope = ee.Terrain.slope(dsm).multiply(math.pi / 180)

        reflected = (
            ghi.multiply(albedo)
            .multiply(slope.cos().multiply(-1).add(1).divide(2))
            .rename(reflected_band)
        )

        return img.addBands(reflected)

    return reflected_irradiance


reflected_irradiance = _builder

__all__ = [
    "reflected_irradiance",
]
