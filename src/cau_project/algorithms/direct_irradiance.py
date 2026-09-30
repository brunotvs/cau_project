import ee

from .config import BaseConfig


class DirectIrradianceConfig(BaseConfig, total=False):
    dni_band: str
    shadow_band: str
    shade_band: str


type BuilderConfig = DirectIrradianceConfig


def _builder(
    user_config: BuilderConfig | None = None,
):

    config: BuilderConfig = user_config or {}
    direct_band: str = config.get("direct_band", "direct_irradiance")
    dni_band: str = config.get("dni_band", "dni")
    shadow_band: str = config.get("shadow_band", "shadow")
    shade_band: str = config.get("shade_band", "shade")

    def direct_irradiance(img: ee.Image):
        dni: ee.Image = img.select(dni_band)
        shadow: ee.Image = img.select(shadow_band)
        shade: ee.Image = img.select(shade_band)

        direct = dni.multiply(shade).multiply(shadow).rename(direct_band)

        return img.addBands(direct)

    return direct_irradiance


direct_irradiance = _builder

__all__ = [
    "direct_irradiance",
]
