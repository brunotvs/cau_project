import math

import ee

from .config import BaseConfig
from .hill_shadow import hill_shadow


class SkyViewFactorConfig(BaseConfig, total=False):
    direct_irradiance: str
    diffuse_irradiance: str
    reflected_irradiance: str


type BuilderConfig = SkyViewFactorConfig


def _builder(
    user_config: BuilderConfig | None = None,
):

    config: BuilderConfig = user_config or {}
    total_band = config.get("output_band", "total_irradiance")
    direct: str = config.get("direct_irradiance", "direct_irradiance")
    diffuse: str = config.get("diffuse_irradiance", "diffuse_irradiance")
    reflected: str = config.get("reflected_irradiance", "reflected_irradiance")

    def total_irradiance(img: ee.Image):
        total = img.expression(
            "direct + diffuse + reflected",
            {
                "direct": img.select(direct),
                "diffuse": img.select(diffuse),
                "reflected": img.select(reflected),
            },
        ).rename(total_band)

        return img.addBands(total)

    return total_irradiance


total_irradiance = _builder

__all__ = [
    "total_irradiance",
]
