import math
from typing import Required, TypedDict

import ee


def solar_altitude(date: ee.Date) -> ee.Number:
    ll = ee.Image.pixelLonLat()
    lon = ll.select("longitude").multiply(math.pi / 180)
    lat = ll.select("latitude").multiply(math.pi / 180)

    doy = ee.Number(date.getRelative("day", "year")).add(1)
    hours = ee.Number(date.get("hour")).add(ee.Number(date.get("minute")).divide(60))

    gamma = doy.subtract(1).multiply(2 * math.pi / 365)
    decl = (
        ee.Number(0.006918)
        .subtract(gamma.cos().multiply(0.399912))
        .add(gamma.sin().multiply(0.070257))
        .subtract(gamma.multiply(2).cos().multiply(0.006758))
        .add(gamma.multiply(2).sin().multiply(0.000907))
    )

    solar_hour = lon.multiply(12 / math.pi).add(hours)
    ha = solar_hour.subtract(12).multiply(math.pi / 12)

    sin_alt = (
        lat.sin()
        .multiply(decl.sin())
        .add(lat.cos().multiply(decl.cos()).multiply(ha.cos()))
    )
    return sin_alt.asin().divide(math.pi / 180)


def erbs_dhi(
    ghi: ee.Image, solar_elevation: ee.Number, day_of_year: ee.Number
) -> ee.Image:
    i0 = ee.Number(1361).multiply(
        ee.Number(1).add(
            ee.Number(0.033).multiply(day_of_year.multiply(2 * math.pi / 365).cos())
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

    def solar_power(img: ee.Image):
        date = img.date()

        hour = date.getRange("hour").start()
        mid = hour.advance(30, "minutes")
        s_alt = solar_altitude(mid)
        day_of_year = date.getRelative("day", "year").add(1)

        ghi: ee.Image = (
            ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY")
            .filterDate(hour)
            .first()
            .select("surface_solar_radiation_downwards_hourly")
            .convolve(ee.Kernel.gaussian(radius=2, sigma=1, units="pixels"))
            .resample("bicubic")
            .divide(3600)
        ).rename(ghi_band)

        dhi = erbs_dhi(ghi, s_alt, day_of_year).rename(dhi_band)

        dni = (
            ghi.subtract(dhi)
            .divide(s_alt.multiply(math.pi / 180).sin())
            .rename(dni_band)
        )

        return img.addBands(ee.Image.cat([ghi, dhi, dni]))

    return solar_power


solar_power = _builder

__all__ = [
    "solar_power",
]
