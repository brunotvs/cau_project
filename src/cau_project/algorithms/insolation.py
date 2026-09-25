import math

import ee

from .config import BaseConfig, calculate_shadow


def solar_geometry_2(lat: ee.Number, lon: ee.Number, date: ee.Date) -> ee.Feature:
    date = ee.Date(date)

    julian_start = ee.Date("-4712-01-01").advance(-37.5, "day")
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
    eccent_earth_orbit = ee.Number(0.016708634).subtract(
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
    # sun_true_anom = geom_mean_anom_sun.add(sun_eq_of_ctr)
    # sun_rad_vector = (
    #     ee.Number(1.000001018)
    #     .multiply(ee.Number(1).subtract(eccent_earth_orbit.pow(2)))
    #     .divide(
    #         eccent_earth_orbit.multiply(
    #             sun_true_anom.multiply(math.pi / 180).cos()
    #         ).add(1)
    #     )
    # )
    sun_app_long = sun_true_long.subtract(0.00569).subtract(
        julian_century.multiply(-1934.136)
        .add(125.04)
        .multiply(math.pi / 180)
        .sin()
        .multiply(0.00478)
    )
    mean_oblic_ecliptic = (
        ee.Number(21.448)
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
        ee.Number(0.00256).multiply(
            julian_century.multiply(-1934.136).add(125.04).multiply(math.pi / 180).cos()
        )
    )
    # sun_rt_ascen = (
    #     sun_app_long.multiply(math.pi / 180)
    #     .cos()
    #     .atan2(
    #         obliq_corr.multiply(math.pi / 180)
    #         .cos()
    #         .multiply(sun_app_long.multiply(math.pi / 180).sin())
    #     )
    #     .divide(math.pi / 180)
    # )
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
    # ha_sunrise = (
    #     ee.Number(90.833)
    #     .multiply(math.pi / 180)
    #     .cos()
    #     .divide(
    #         ee.Number(lat)
    #         .multiply(math.pi / 180)
    #         .cos()
    #         .multiply(sun_declin.multiply(math.pi / 180).cos())
    #     )
    #     .subtract(
    #         ee.Number(lat)
    #         .multiply(math.pi / 180)
    #         .tan()
    #         .multiply(sun_declin.multiply(math.pi / 180).tan())
    #     )
    #     .mod(1)
    #     .acos()
    #     .divide(math.pi / 180)
    # )
    # solar_noon = (
    #     date.getRange("day")
    #     .start()
    #     .advance(
    #         ee.Number(lon).multiply(-4).add(720).subtract(eq_of_time),
    #         "minute",
    #     )
    # )
    # sunrise_time = solar_noon.advance(
    #     ha_sunrise.multiply(-4),
    #     "minute",
    # )

    # sunset_time = solar_noon.advance(
    #     ha_sunrise.multiply(4),
    #     "minute",
    # )
    # sunlight_duration = ha_sunrise.multiply(8)
    true_solar_time = date.advance(eq_of_time.add(ee.Number(lon).multiply(4)), "minute")
    hour_angle = (
        true_solar_time.difference(true_solar_time.getRange("day").start(), "minute")
        .divide(4)
        .subtract(180)
    )
    solar_zenith_angle = (
        ee.Number(lat)
        .multiply(math.pi / 180)
        .sin()
        .multiply(sun_declin.multiply(math.pi / 180).sin())
        .add(
            ee.Number(lat)
            .multiply(math.pi / 180)
            .cos()
            .multiply(sun_declin.multiply(math.pi / 180).cos())
            .multiply(hour_angle.multiply(math.pi / 180).cos())
        )
        .mod(1)
        .acos()
        .divide(math.pi / 180)
    )
    solar_elevation_angle = ee.Number(90).subtract(solar_zenith_angle)
    approx_atmospheric_refraction = ee.Number(
        ee.Algorithms.If(
            solar_elevation_angle.gt(85),
            0,
            ee.Algorithms.If(
                solar_elevation_angle.gt(5),
                ee.Number(58.1)
                .divide(solar_elevation_angle.multiply(math.pi / 180).tan())
                .subtract(
                    ee.Number(0.07).divide(
                        solar_elevation_angle.multiply(math.pi / 180).tan().pow(3)
                    )
                )
                .add(
                    ee.Number(0.000086).divide(
                        solar_elevation_angle.multiply(math.pi / 180).tan().pow(5)
                    )
                ),
                ee.Algorithms.If(
                    solar_elevation_angle.gt(-0.575),
                    solar_elevation_angle.multiply(0.711)
                    .subtract(12.79)
                    .multiply(solar_elevation_angle)
                    .add(103.4)
                    .multiply(solar_elevation_angle)
                    .subtract(518.2)
                    .multiply(solar_elevation_angle)
                    .add(1735),
                    ee.Number(-20.772).divide(
                        solar_elevation_angle.multiply(math.pi / 180).tan()
                    ),
                ),
            ),
        )
    ).divide(3600)

    solar_elevation_corrected_for_atm_refraction = solar_elevation_angle.add(
        approx_atmospheric_refraction
    )
    solar_azimuth_angle = (
        hour_angle.signum()
        .multiply(
            ee.Number(lat)
            .multiply(math.pi / 180)
            .sin()
            .multiply(solar_zenith_angle.multiply(math.pi / 180).cos())
            .subtract(sun_declin.multiply(math.pi / 180).sin())
            .divide(
                ee.Number(lat)
                .multiply(math.pi / 180)
                .cos()
                .multiply(solar_zenith_angle.multiply(math.pi / 180).sin())
            )
            .mod(1)
            .acos()
            .divide(math.pi / 180)
        )
        .add(180)
    )
    solar_zenith_corrected_for_atm_refraction = ee.Number(90).subtract(
        solar_elevation_corrected_for_atm_refraction
    )

    return ee.Feature(
        None,
        {
            "azimuth": solar_azimuth_angle,
            "zenith": solar_zenith_corrected_for_atm_refraction,
            "latitude": lat,
            "longitude": lon,
            "date": date,
            # "julian_day": julian_day,
            # "julian_century": julian_century,
            # "geom_mean_long_sun": geom_mean_long_sun,
            # "geom_mean_anom_sun": geom_mean_anom_sun,
            # "eccent_earth_orbit": eccent_earth_orbit,
            # "sun_eq_of_ctr": sun_eq_of_ctr,
            # "sun_true_long": sun_true_long,
            # "sun_true_anom": sun_true_anom,
            # "sun_rad_vector": sun_rad_vector,
            # "sun_app_long": sun_app_long,
            # "mean_oblic_ecliptic": mean_oblic_ecliptic,
            # "obliq_corr": obliq_corr,
            # "sun_rt_ascen": sun_rt_ascen,
            # "sun_declin": sun_declin,
            # "var_gamma": var_gamma,
            # "eq_of_time": eq_of_time,
            # "ha_sunrise": ha_sunrise,
            # "solar_noon": solar_noon,
            # "sunrise_time": sunrise_time,
            # "sunset_time": sunset_time,
            # "sunlight_duartion": sunlight_duration,
            # "true_solar_time": true_solar_time,
            # "hour_angle": hour_angle,
            # "solar_zenith_angle": solar_zenith_angle,
            # "solar_elevation_angle": solar_elevation_angle,
            # "approx_atmospheric_refraction": approx_atmospheric_refraction,
            # "solar_elevation_corrected_for_atm_refraction": solar_elevation_corrected_for_atm_refraction,
            # "solar_azimut_angle": solar_azimuth_angle,
            # "solar_zenith_corrected_for_atm_refraction": solar_zenith_corrected_for_atm_refraction,
        },
    )


def sample_shadow(feat: ee.ComputedObject) -> ee.Image:
    feat = ee.Feature(feat)
    lat = ee.Number(feat.get("latitude"))
    lon = ee.Number(feat.get("longitude"))
    precision = ee.Number(feat.get("angular_precision"))
    half_precision = precision.divide(2)

    shadow_tile = ee.Image(feat.get("shadow_image"))

    lat_lon = ee.Image.pixelLonLat()
    img_lon: ee.Image = lat_lon.select("longitude")

    diff_lon = img_lon.subtract(lon).add(180).mod(360).subtract(180)
    diff_lon = diff_lon.where(diff_lon.lt(-180), diff_lon.add(360))
    lon_mask = diff_lon.abs().lte(half_precision)

    img_lat: ee.Image = lat_lon.select("latitude")

    diff_lat = img_lat.subtract(lat).add(90).mod(180).subtract(90)
    lat_mask = diff_lat.abs().lte(half_precision)

    cell_active = lon_mask.And(lat_mask)

    return shadow_tile.updateMask(cell_active)


class InsolationConfig(BaseConfig, total=False):
    shadow_band: str
    insolation_band: str
    bh_band: str
    dem_band: str
    angular_precision: float
    geometry: ee.Geometry


type BuilderConfig = InsolationConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    shadow_band = config.get("shadow_band", "shadow")
    insolation_band = config.get("insolation_band", "insolation")
    angular_precision: float = config.get("angular_precision", 1)
    bh_band: str = config.get("bh_band", "bh")
    dem_band: str = config.get("dem_band", "dem")

    geometry: ee.Geometry = config.get("geometry", ee.Geometry.BBox(-180, -90, 180, 90))

    bounds = geometry.bounds()
    coords = ee.List(bounds.coordinates().get(0))

    sw = ee.List(coords.get(0))
    ne = ee.List(coords.get(2))

    lon_min = ee.Number(sw.get(0)).max(-180)
    lat_min = ee.Number(sw.get(1)).max(-90)
    lon_max = ee.Number(ne.get(0)).min(180)
    lat_max = ee.Number(ne.get(1)).min(90)

    lons = ee.List.sequence(lon_min, lon_max, angular_precision)
    lats = ee.List.sequence(lat_min, lat_max, angular_precision)

    def insolation(img: ee.Image):
        building_heights = img.select(bh_band)
        dem = img.select(dem_band)

        sun_geometry = lons.map(
            lambda lon: lats.map(lambda lat: solar_geometry_2(lat, lon, img.date()))
        ).flatten()

        img = img.addBands(
            ee.ImageCollection(
                sun_geometry.map(
                    lambda entry: ee.Feature(entry).set(
                        {
                            "angular_precision": angular_precision,
                            "shadow_image": calculate_shadow(
                                ee.Feature(
                                    ee.Feature(entry).set(
                                        "dem",
                                        dem,
                                        "building_heights",
                                        building_heights,
                                    )
                                )
                            ),
                        }
                    )
                ).map(sample_shadow)
            )
            .mosaic()
            .unmask(0)
            .rename(shadow_band)
        )

        return img

    return insolation


insolation = _builder

__all__ = [
    "insolation",
]
