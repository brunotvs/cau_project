import math
from typing import TypedDict

import ee


def solar_geometry(date: ee.Date) -> ee.Image:
    date = ee.Date(date)
    julian_start = ee.Date("-4712-01-01").advance(-37.5, "day")

    lon_lat = ee.Image.pixelLonLat()
    lat: ee.Image = lon_lat.select("latitude")
    lon: ee.Image = lon_lat.select("longitude")

    julian_day = date.difference(
        julian_start,
        "day",
    )
    julian_century = julian_day.subtract(2451545).divide(36525)
    geom_mean_long_sun = (
        julian_century.multiply(julian_century.multiply(0.0003032).add(36000.76983))
        .add(280.46646)
        .mod(360)
    )
    geom_mean_anom_sun = julian_century.multiply(
        julian_century.multiply(0.0001537).add(35999.05029)
    ).add(357.52911)
    eccent_earth_orbit = ee.Image(0.016708634).subtract(
        julian_century.multiply(julian_century.multiply(0.0000001267).add(0.000042037))
    )
    sun_eq_of_ctr = (
        geom_mean_anom_sun.multiply(math.pi / 180)
        .sin()
        .multiply(
            ee.Number(1.914602).subtract(
                julian_century.multiply(julian_century.multiply(0.000014).add(0.004817))
            )
        )
        .add(
            geom_mean_anom_sun.multiply(2 * math.pi / 180)
            .sin()
            .multiply(julian_century.multiply(-0.000101).add(0.019993))
        )
        .add(geom_mean_anom_sun.multiply(3 * math.pi / 180).sin().multiply(0.000289))
    )
    sun_true_long = geom_mean_long_sun.add(sun_eq_of_ctr)
    sun_true_anom = geom_mean_anom_sun.add(sun_eq_of_ctr)
    sun_rad_vector = (
        ee.Image(1.000001018)
        .multiply(ee.Image(1).subtract(eccent_earth_orbit.pow(2)))
        .divide(
            eccent_earth_orbit.multiply(
                sun_true_anom.multiply(math.pi / 180).cos()
            ).add(1)
        )
    )
    sun_app_long = sun_true_long.subtract(0.00569).subtract(
        julian_century.multiply(-1934.136)
        .add(125.04)
        .multiply(math.pi / 180)
        .sin()
        .multiply(0.00478)
    )
    mean_oblic_ecliptic = (
        ee.Image(21.448)
        .subtract(
            julian_century.multiply(
                julian_century.multiply(
                    julian_century.multiply(-0.001813).add(0.00059)
                ).add(46.815)
            )
        )
        .divide(60)
        .add(26)
        .divide(60)
        .add(23)
    )
    obliq_corr = mean_oblic_ecliptic.add(
        ee.Image(0.00256).multiply(
            julian_century.multiply(-1934.136).add(125.04).multiply(math.pi / 180).cos()
        )
    )
    sun_rt_ascen = (
        ee.Image(sun_app_long)
        .multiply(math.pi / 180)
        .cos()
        .atan2(
            obliq_corr.multiply(math.pi / 180)
            .cos()
            .multiply(sun_app_long.multiply(math.pi / 180).sin())
        )
        .divide(math.pi / 180)
    )
    sun_declin = (
        obliq_corr.multiply(math.pi / 180)
        .sin()
        .multiply(sun_app_long.multiply(math.pi / 180).sin())
        .asin()
        .divide(math.pi / 180)
    )
    var_gamma = (
        obliq_corr.divide(2)
        .multiply(math.pi / 180)
        .tan()
        .multiply(obliq_corr.divide(2).multiply(math.pi / 180).tan())
    )
    eq_of_time = (
        var_gamma.multiply(geom_mean_long_sun.multiply(math.pi / 180).multiply(2).sin())
        .subtract(
            eccent_earth_orbit.multiply(2).multiply(
                geom_mean_anom_sun.multiply(math.pi / 180).sin()
            )
        )
        .add(
            eccent_earth_orbit.multiply(4)
            .multiply(var_gamma)
            .multiply(geom_mean_anom_sun.multiply(math.pi / 180).sin())
            .multiply(geom_mean_long_sun.multiply(math.pi / 180).multiply(2).cos())
        )
        .subtract(
            var_gamma.pow(2)
            .multiply(0.5)
            .multiply(geom_mean_long_sun.multiply(math.pi / 180).multiply(4).sin())
        )
        .subtract(
            eccent_earth_orbit.pow(2)
            .multiply(1.25)
            .multiply(geom_mean_anom_sun.multiply(math.pi / 180).multiply(2).sin())
        )
        .divide(math.pi / 180)
        .multiply(4)
    )
    ha_sunrise = (
        ee.Image(90.833)
        .multiply(math.pi / 180)
        .cos()
        .divide(
            lat.multiply(math.pi / 180)
            .cos()
            .multiply(sun_declin.multiply(math.pi / 180).cos())
        )
        .subtract(
            lat.multiply(math.pi / 180)
            .tan()
            .multiply(sun_declin.multiply(math.pi / 180).tan())
        )
        .acos()
        .divide(math.pi / 180)
    )

    solar_noon = ee.Image.constant(date.getRange("day").start().millis()).add(
        lon.multiply(-4).add(720).subtract(eq_of_time).multiply(60 * 1000)
    )
    sunrise_time = solar_noon.add(ha_sunrise.multiply(-4 * 60 * 1000))

    sunset_time = solar_noon.add(
        ha_sunrise.multiply(4 * 60 * 1000),
    )

    sunlight_duration = ha_sunrise.multiply(8)

    true_solar_time = ee.Image.constant(date.millis()).add(
        eq_of_time.add(lon.multiply(4)).multiply(60 * 1000)
    )

    hour_angle = (
        true_solar_time.mod(24 * 60 * 60 * 1000)
        .divide(1000 * 60)
        .divide(4)
        .subtract(180)
    )

    solar_zenith_angle = (
        lat.multiply(math.pi / 180)
        .sin()
        .multiply(sun_declin.multiply(math.pi / 180).sin())
        .add(
            lat.multiply(math.pi / 180)
            .cos()
            .multiply(sun_declin.multiply(math.pi / 180).cos())
            .multiply(hour_angle.multiply(math.pi / 180).cos())
        )
        .acos()
        .divide(math.pi / 180)
    )

    solar_elevation_angle = ee.Image(90).subtract(solar_zenith_angle)

    approx_atmospheric_refraction = (
        ee.Image(0)
        .where(
            solar_elevation_angle.gt(5).And(solar_elevation_angle.lte(85)),
            ee.Image(58.1)
            .divide(solar_elevation_angle.multiply(math.pi / 180).tan())
            .subtract(
                ee.Image(0.07).divide(
                    solar_elevation_angle.multiply(math.pi / 180).tan().pow(3)
                )
            )
            .add(
                ee.Image(0.000086).divide(
                    solar_elevation_angle.multiply(math.pi / 180).tan().pow(5)
                )
            ),
        )
        .where(
            solar_elevation_angle.gt(-0.575).And(solar_elevation_angle.lte(5)),
            solar_elevation_angle.multiply(0.711)
            .subtract(12.79)
            .multiply(solar_elevation_angle)
            .add(103.4)
            .multiply(solar_elevation_angle)
            .subtract(518.2)
            .multiply(solar_elevation_angle)
            .add(1735),
        )
        .where(
            solar_elevation_angle.lte(-0.575),
            ee.Image(-20.772).divide(
                solar_elevation_angle.multiply(math.pi / 180).tan()
            ),
        )
    ).divide(3600)

    solar_elevation_corrected_for_atm_refraction = solar_elevation_angle.add(
        approx_atmospheric_refraction
    )

    solar_azimuth_angle = (
        hour_angle.signum()
        .multiply(
            lat.multiply(math.pi / 180)
            .sin()
            .multiply(solar_zenith_angle.multiply(math.pi / 180).cos())
            .subtract(sun_declin.multiply(math.pi / 180).sin())
            .divide(
                lat.multiply(math.pi / 180)
                .cos()
                .multiply(solar_zenith_angle.multiply(math.pi / 180).sin())
            )
            .acos()
            .divide(math.pi / 180)
        )
        .add(180)
    )
    solar_zenith_corrected_for_atm_refraction = ee.Image(90).subtract(
        solar_elevation_corrected_for_atm_refraction
    )

    return (
        ee.Image(solar_azimuth_angle)
        .rename("azimuth")
        .addBands(
            ee.Image(solar_zenith_corrected_for_atm_refraction).rename("zenith"),
        )
        .addBands(ee.Image(julian_day).rename("julian_day"))
        .addBands(ee.Image(julian_century).rename("julian_century"))
        .addBands(ee.Image(geom_mean_long_sun).rename("geom_mean_long_sun"))
        .addBands(ee.Image(geom_mean_anom_sun).rename("geom_mean_anom_sun"))
        .addBands(ee.Image(eccent_earth_orbit).rename("eccent_earth_orbit"))
        .addBands(ee.Image(sun_eq_of_ctr).rename("sun_eq_of_ctr"))
        .addBands(ee.Image(sun_true_long).rename("sun_true_long"))
        .addBands(ee.Image(sun_true_anom).rename("sun_true_anom"))
        .addBands(ee.Image(sun_rad_vector).rename("sun_rad_vector"))
        .addBands(ee.Image(sun_app_long).rename("sun_app_long"))
        .addBands(ee.Image(mean_oblic_ecliptic).rename("mean_oblic_ecliptic"))
        .addBands(ee.Image(obliq_corr).rename("obliq_corr"))
        .addBands(ee.Image(sun_rt_ascen).rename("sun_rt_ascen"))
        .addBands(ee.Image(sun_declin).rename("sun_declin"))
        .addBands(ee.Image(var_gamma).rename("var_gamma"))
        .addBands(ee.Image(eq_of_time).rename("eq_of_time"))
        .addBands(ee.Image(ha_sunrise).rename("ha_sunrise"))
        .addBands(ee.Image(solar_noon).rename("solar_noon"))
        .addBands(ee.Image(sunrise_time).rename("sunrise_time"))
        .addBands(ee.Image(sunset_time).rename("sunset_time"))
        .addBands(ee.Image(sunlight_duration).rename("sunlight_duartion"))
        .addBands(ee.Image(true_solar_time).rename("true_solar_time"))
        .addBands(ee.Image(hour_angle).rename("hour_angle"))
        .addBands(ee.Image(solar_zenith_angle).rename("solar_zenith_angle"))
        .addBands(ee.Image(solar_elevation_angle).rename("solar_elevation_angle"))
        .addBands(
            ee.Image(approx_atmospheric_refraction).rename(
                "approx_atmospheric_refraction"
            )
        )
        .addBands(
            ee.Image(solar_elevation_corrected_for_atm_refraction).rename(
                "solar_elevation_corrected_for_atm_refraction"
            )
        )
        .addBands(ee.Image(solar_azimuth_angle).rename("solar_azimut_angle"))
        .addBands(
            ee.Image(solar_zenith_corrected_for_atm_refraction).rename(
                "solar_zenith_corrected_for_atm_refraction"
            )
        )
    )


def sample_shadow(dic: ee.Dictionary) -> ee.Image:
    dic = ee.Dictionary(dic)

    solar_geometry = ee.Image(dic.get("solar_geometry"))
    azimuth_img = solar_geometry.select("azimuth")
    zenith_img = solar_geometry.select("zenith")

    az = ee.Number(dic.get("azimuth"))
    ze = ee.Number(dic.get("zenith"))
    az_half = ee.Number(dic.get("az_step")).divide(2.0)
    ze_half = ee.Number(dic.get("ze_step")).divide(2.0)

    shadow_tile = ee.Image(
        ee.ImageCollection(dic.get("shadow_collection"))
        .filter(ee.Filter.eq("azimuth", az))
        .filter(ee.Filter.eq("zenith", ze))
        .first()
    )

    diff_az = azimuth_img.subtract(az).add(180.0).mod(360.0).subtract(180.0)
    diff_az = diff_az.where(diff_az.lt(-180.0), diff_az.add(360.0))
    az_mask = diff_az.abs().lte(az_half)

    ze_min = ze.subtract(ze_half).max(0.0)
    ze_max = ze.add(ze_half).min(90.0)
    ze_mask = zenith_img.gte(ze_min).And(zenith_img.lt(ze_max))

    cell_active = az_mask.And(ze_mask)  # .And(zenith_img.lt(89.5))

    return shadow_tile.updateMask(cell_active)


def calculate_shadow(sun_position: ee.Dictionary) -> ee.Image:
    sun_position = ee.Dictionary(sun_position)

    azimuth: ee.Number = ee.Number(sun_position.get("azimuth"))
    zenith: ee.Number = ee.Number(sun_position.get("zenith"))
    dsm = ee.Image(sun_position.get("dsm"))

    weight = zenith.multiply(math.pi / 180.0).cos()

    shadow = ee.Image(
        ee.Terrain.hillShadow(dsm, azimuth, zenith, 100)
        .set("weight", weight)
        .set("azimuth", azimuth)
        .set("zenith", zenith)
    )

    return shadow


class SkyViewFactorConfig(TypedDict, total=False):
    svf_band: str
    shadow_band: str
    insolation_band: str
    dsm_band: str
    num_directions: int
    num_elevations: int


type BuilderConfig = SkyViewFactorConfig


def _builder(
    user_config: BuilderConfig | None = None,
):

    config: BuilderConfig = user_config or {}
    svf_band = config.get("svf_band", "svf")
    shadow_band = config.get("shadow_band", "shadow")
    insolation_band = config.get("insolation_band", "insolation")
    dsm_band: str = config.get("dsm_band", "dsm")
    num_directions: int = config.get("num_directions", 16)
    num_elevations: int = config.get("num_elevations", 8)

    az_step = ee.Number(360 / num_directions)
    azimuths = ee.List.sequence(0, num_directions - 1).map(
        lambda value: ee.Number(value).multiply(az_step)
    )

    ze_step = ee.Number(90 / (num_elevations - 1))
    zeniths = (
        ee.List.sequence(0, num_elevations - 1)
        .map(
            lambda value: (
                ee.Number(value).multiply(ze_step) if num_elevations > 1 else 0
            )
        )
        .set(0, 0.001)
    )

    sun_positions = azimuths.map(
        lambda az: zeniths.map(lambda ze: ee.Dictionary({"azimuth": az, "zenith": ze}))
    ).flatten()

    def sky_view_factor(img: ee.Image):
        dsm = img.select(dsm_band)

        shadow_collection = ee.ImageCollection.fromImages(
            sun_positions.map(lambda entry: ee.Dictionary(entry).set("dsm", dsm)).map(
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

        img = img.addBands(
            ee.ImageCollection.fromImages(
                sun_positions.map(
                    lambda entry: (
                        ee.Dictionary(entry)
                        .set("solar_geometry", solar_geometry(img.date()))
                        .set("shadow_collection", shadow_collection)
                        .set("ze_step", ze_step)
                        .set("az_step", az_step)
                    )
                ).map(sample_shadow)
            )
            .mosaic()
            .unmask(0)
            .rename(shadow_band)
        )

        # img = img.addBands(solar_geometry(img.date()))

        return img

    return sky_view_factor


svf = _builder

__all__ = [
    "svf",
]
