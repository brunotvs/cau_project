import ee

from .config import BaseConfig, calculate_shadow


class SkyViewFactorConfig(BaseConfig, total=False):
    dsm_band: str
    num_directions: int
    num_elevations: int


type BuilderConfig = SkyViewFactorConfig


def _builder(
    user_config: BuilderConfig | None = None,
):

    config: BuilderConfig = user_config or {}
    svf_band = config.get("output_band", "svf")
    dsm_band: str = config.get("dsm_band", "dsm")
    num_directions: int = config.get("num_directions", 16)
    num_elevations: int = config.get("num_elevations", 8)

    az_step = ee.Number(360 / num_directions)
    azimuths = ee.List.sequence(0, num_directions - 1).map(
        lambda value: ee.Number(value).multiply(az_step)
    )

    ze_step = ee.Number(90 / (num_elevations - 1))
    zeniths = ee.List.sequence(0, num_elevations - 1).map(
        lambda value: ee.Number(value).multiply(ze_step) if num_elevations > 1 else 0
    )

    sun_positions = azimuths.map(
        lambda az: zeniths.map(
            lambda ze: ee.Feature(None, {"azimuth": az, "zenith": ze})
        )
    ).flatten()

    def sky_view_factor(img: ee.Image):
        dsm = img.select(dsm_band)

        shadow_collection = ee.ImageCollection.fromImages(
            sun_positions.map(lambda entry: ee.Feature(entry).set("dsm", dsm)).map(
                calculate_shadow
            )
        )

        img = img.addBands(
            shadow_collection.map(
                lambda img: ee.Image(img).multiply(ee.Number(img.get("weight")))
            )
            .sum()
            .divide(ee.Number(shadow_collection.aggregate_sum("weight")))
            .rename(svf_band)
        )

        return img

    return sky_view_factor


svf = _builder

__all__ = [
    "svf",
]
