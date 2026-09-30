import math
from typing import Required, TypedDict

import ee


def erbs_dhi(
    ghi: ee.Image, solar_elevation: ee.Number, day_of_year: ee.Number
) -> ee.Image:
    i0 = ee.Number(1361).multiply(
        ee.Number(1 + 0.033).multiply(
            day_of_year.multiply(2 * math.pi).divide(365).cos()
        )
    )
    kt = ghi.divide(solar_elevation.multiply(math.pi / 180).sin().multiply(i0)).clamp(
        0, 1
    )

    kd_low = kt.multiply(-0.09).add(1)
    kd_mid = (
        kt.multiply(-0.1604)
        .add(0.9511)
        .add(kt.pow(2).multiply(4.388))
        .subtract(kt.pow(3).multiply(16.638))
        .add(kt.pow(4).multiply(12.336))
    )
    kd = ee.Image(0.165)
    kd = kd.where(kt.lte(0.8), kd_mid).where(kt.lte(0.22), kd_low)

    return ghi.multiply(kd)


class SolarEnergyConfig(TypedDict, total=False):
    ghi_band: str
    dni_band: str
    dhi_band: str
    zenith: Required[float | ee.Number]


type BuilderConfig = SolarEnergyConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {"zenith": 60}
    ghi_band = config.get("ghi_band", "ghi")
    dni_band = config.get("dni_band", "dni")
    dhi_band = config.get("dhi_band", "dhi")
    zenith = config.get("zenith")

    def solar_power(img: ee.Image):

        solar_elevation = ee.Number(90).subtract(zenith)

        hour = img.date().getRange("hour")
        day_of_year = img.date().getRelative("day", "year")

        ghi: ee.Image = (
            ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY")
            .filterDate(hour)
            .first()
            .select("surface_solar_radiation_downwards_hourly")
            .convolve(ee.Kernel.gaussian(radius=2, sigma=1, units="pixels"))
            .resample("bicubic")
            .divide(3600)
        ).rename(ghi_band)

        dhi = erbs_dhi(ghi, solar_elevation, day_of_year).rename(dhi_band)

        dni = (
            ghi.subtract(dhi)
            .divide(solar_elevation.multiply(math.pi / 180).sin())
            .rename(dni_band)
        )

        return img.addBands(ee.Image.cat([ghi, dhi, dni]))

    return solar_power


solar_power = _builder

__all__ = [
    "solar_power",
]
