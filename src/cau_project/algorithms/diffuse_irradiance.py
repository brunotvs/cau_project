import math

import ee

from .config import BaseConfig


class DirectIrradianceConfig(BaseConfig, total=False):
    dsm_band: str
    svf_band: str
    dhi_band: str


type BuilderConfig = DirectIrradianceConfig


def _builder(
    user_config: BuilderConfig | None = None,
):

    config: BuilderConfig = user_config or {}
    diffuse_band: str = config.get("output_band", "diffuse_irradiance")
    dsm_band: str = config.get("dsm_band", "dsm")
    dhi_band: str = config.get("dhi_band", "dhi")
    svf_band: str = config.get("svf_band", "svf")

    def diffuse_irradiance(img: ee.Image):
        dsm: ee.Image = img.select(dsm_band)
        dhi: ee.Image = img.select(dhi_band)
        svf: ee.Image = img.select(svf_band)

        slope = ee.Terrain.slope(dsm).multiply(math.pi / 180)

        diffuse = (
            dhi.multiply(slope.cos().add(1).divide(2))
            .multiply(svf)
            .rename(diffuse_band)
        )

        return img.addBands(diffuse)

    return diffuse_irradiance


diffuse_irradiance = _builder

__all__ = [
    "diffuse_irradiance",
]
