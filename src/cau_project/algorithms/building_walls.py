import ee

from .config import BaseConfig


class HillShadowConfig(BaseConfig, total=False):
    bh_band: str
    walls_band: str
    threshold: float
    sigma: float


type BuilderConfig = HillShadowConfig


def _builder(
    user_config: BuilderConfig | None = None,
):

    config: BuilderConfig = user_config or {}
    walls_band = config.get("output_band", "walls")
    bh_band: str = config.get("bh_band", "bh")
    threshold: float = config.get("threshold", 3)
    sigma: float = config.get("sigma", 1)

    def building_walls(img: ee.Image):
        bh = img.select(bh_band).unmask(0)
        walls = ee.Image(ee.Algorithms.CannyEdgeDetector(bh, threshold, sigma)).rename(
            walls_band
        )

        return img.addBands(walls)

    return building_walls


walls = _builder

__all__ = [
    "walls",
]
