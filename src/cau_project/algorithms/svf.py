import math

import ee

from .config import BaseConfig
from .hill_shadow import hill_shadow


class SkyViewFactorConfig(BaseConfig, total=False):
    dem_band: str
    bh_band: str
    neighborhood_size: int
    num_directions: int
    num_elevations: int


type BuilderConfig = SkyViewFactorConfig


def _builder(
    user_config: BuilderConfig | None = None,
):

    config: BuilderConfig = user_config or {}
    svf_band = config.get("output_band", "svf")
    dem_band: str = config.get("dem_band", "dem")
    bh_band: str = config.get("bh_band", "bh")
    walls_band: str = config.get("walls_band", "walls")
    num_directions: int = config.get("num_directions", 16)
    num_elevations: int = config.get("num_elevations", 8)
    neighborhood_size: int = config.get("neighborhood_size", 200)

    az_step = ee.Number(360 / num_directions)
    azimuths = ee.List.sequence(0, num_directions - 1).map(
        lambda value: ee.Number(value).multiply(az_step)
    )

    ze_step = ee.Number(90 / (num_elevations - 1))
    zeniths = ee.List.sequence(0, num_elevations - 1).map(
        lambda value: ee.Number(value).multiply(ze_step) if num_elevations > 1 else 0
    )

    sun_positions = ee.FeatureCollection(
        azimuths.map(
            lambda az: zeniths.map(
                lambda ze: ee.Feature(None, {"azimuth": az, "zenith": ze})
            )
        ).flatten()
    )

    def sky_view_factor(img: ee.Image):
        shadow_collection = ee.ImageCollection(
            sun_positions.map(
                lambda entry: hill_shadow(
                    {
                        "azimuth": entry.get("azimuth"),
                        "zenith": entry.get("zenith"),
                        "bh_band": bh_band,
                        "dem_band": dem_band,
                        "walls_band": walls_band,
                        "neighborhood_size": neighborhood_size,
                        "output_band": "shadow",
                    }
                )(
                    img
                ).set(
                    "w", ee.Number(entry.get("zenith")).multiply(math.pi / 180.0).cos()
                )
            )
        )

        img = img.addBands(
            shadow_collection.map(
                lambda img: ee.Image(img.select("shadow")).multiply(
                    ee.Number(img.get("w"))
                )
            )
            .sum()
            .divide(ee.Number(shadow_collection.aggregate_sum("w")))
            .rename(svf_band)
        )

        return img

    return sky_view_factor


svf = _builder

__all__ = [
    "svf",
]
