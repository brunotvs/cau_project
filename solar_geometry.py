import math

import ee


def solar_geometry1(
    date: ee.Date,
    lat_deg: float = -23.753554443082365,
    lon_deg: float = -46.39906192606612,
) -> ee.Dictionary:
    date = ee.Date(date)

    # 1. Dia fracionário do ano (gamma em radianos)
    doy = date.getRelative("day", "year").add(1)
    # Hora decimal UTC
    start_of_utc_day = ee.Date(date.format("YYYY-MM-dd", "UTC"))
    hour_utc = date.difference(start_of_utc_day, "hour")

    # Ângulo do ano (radianos)
    gamma = (
        doy.subtract(1)
        .add(hour_utc.subtract(12.0).divide(24.0))
        .multiply(2.0 * math.pi / 365.0)
    )

    # 2. Equação do Tempo (minutos)
    eqtime = (
        gamma.multiply(2)
        .cos()
        .multiply(-3.2)
        .add(gamma.sin().multiply(229.18))
        .subtract(gamma.cos().multiply(107.5))
        .subtract(gamma.multiply(2).sin().multiply(7.8))
    )

    # 3. Declinação Solar (radianos)
    decl = (
        ee.Number(0.006918)
        .subtract(gamma.cos().multiply(0.399912))
        .add(gamma.sin().multiply(0.070257))
        .subtract(gamma.multiply(2).cos().multiply(0.006758))
        .add(gamma.multiply(2).sin().multiply(0.000907))
    )

    lat = ee.Number(lat_deg).multiply(math.pi / 180.0)
    lon = ee.Number(lon_deg)

    # 4. True Solar Time (TST) em minutos
    # lon * 4 minutos por grau
    tst = hour_utc.multiply(60.0).add(eqtime).add(lon.multiply(4.0))

    # 5. Ângulo Horário (HA): (tst / 4) - 180 graus -> convertido para radianos
    ha_deg = tst.divide(4.0).subtract(180.0)
    # Normaliza ha para [-180, 180]
    ha_deg = ha_deg.add(180.0).mod(360.0).subtract(180.0)
    ha = ha_deg.multiply(math.pi / 180.0)

    # 6. Cosseno do Zênite
    cos_zenith = (
        lat.sin()
        .multiply(decl.sin())
        .add(lat.cos().multiply(decl.cos()).multiply(ha.cos()))
        .clamp(-1.0, 1.0)
    )

    zenith_rad = cos_zenith.acos()
    sin_zenith = zenith_rad.sin().max(1e-6)

    # 7. Azimute Solar
    cos_azimuth = (
        lat.sin()
        .multiply(cos_zenith)
        .subtract(decl.sin())
        .divide(lat.cos().multiply(sin_zenith))
        .clamp(-1.0, 1.0)
    )

    azimuth_rad = cos_azimuth.acos()
    # Se o ângulo horário for maior que 0 (tarde), azimute = 360° - azimute
    azimuth_rad = ee.Number(
        ee.Algorithms.If(
            ha.gt(0), ee.Number(2.0 * math.pi).subtract(azimuth_rad), azimuth_rad
        )
    )

    zenith_deg = zenith_rad.multiply(180.0 / math.pi)
    azimuth_deg = azimuth_rad.multiply(180.0 / math.pi)

    return ee.Dictionary(
        {
            "zenith": zenith_deg,
            "azimuth": azimuth_deg,
            "decl": decl,
            "eqtime": eqtime,
            "ha": ha,
            "date": date,
        }
    )


def solar_geometry(
    date: ee.Date,
    lat_deg: float = -23,
    lon_deg: float = -46,
) -> ee.Dictionary:
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
    sun_true_anom = geom_mean_anom_sun.add(sun_eq_of_ctr)
    sun_rad_vector = (
        ee.Number(1.000001018)
        .multiply(ee.Number(1).subtract(eccent_earth_orbit.pow(2)))
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
    sun_rt_ascen = (
        sun_app_long.multiply(math.pi / 180)
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
        ee.Number(90.833)
        .multiply(math.pi / 180)
        .cos()
        .divide(
            ee.Number(lat_deg)
            .multiply(math.pi / 180)
            .cos()
            .multiply(sun_declin.multiply(math.pi / 180).cos())
        )
        .subtract(
            ee.Number(lat_deg)
            .multiply(math.pi / 180)
            .tan()
            .multiply(sun_declin.multiply(math.pi / 180).tan())
        )
        .acos()
        .divide(math.pi / 180)
    )
    solar_noon = (
        date.getRange("day")
        .start()
        .advance(
            ee.Number(lon_deg).multiply(-4).add(720).subtract(eq_of_time),
            "minute",
        )
    )
    sunrise_time = solar_noon.advance(
        ha_sunrise.multiply(-4),
        "minute",
    )

    sunset_time = solar_noon.advance(
        ha_sunrise.multiply(4),
        "minute",
    )

    sunlight_duration = ha_sunrise.multiply(8)
    true_solar_time = date.advance(
        eq_of_time.add(ee.Number(lon_deg).multiply(4)), "minute"
    )
    hour_angle = (
        true_solar_time.difference(true_solar_time.getRange("day").start(), "minute")
        .divide(4)
        .subtract(180)
    )
    solar_zenith_angle = (
        ee.Number(lat_deg)
        .multiply(math.pi / 180)
        .sin()
        .multiply(sun_declin.multiply(math.pi / 180).sin())
        .add(
            ee.Number(lat_deg)
            .multiply(math.pi / 180)
            .cos()
            .multiply(sun_declin.multiply(math.pi / 180).cos())
            .multiply(hour_angle.multiply(math.pi / 180).cos())
        )
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
            ee.Number(lat_deg)
            .multiply(math.pi / 180)
            .sin()
            .multiply(solar_zenith_angle.multiply(math.pi / 180).cos())
            .subtract(sun_declin.multiply(math.pi / 180).sin())
            .divide(
                ee.Number(lat_deg)
                .multiply(math.pi / 180)
                .cos()
                .multiply(solar_zenith_angle.multiply(math.pi / 180).sin())
            )
            .acos()
            .divide(math.pi / 180)
        )
        .add(180)
    )
    solar_zenith_corrected_for_atm_refraction = ee.Number(90).subtract(
        solar_elevation_corrected_for_atm_refraction
    )

    return ee.Dictionary(
        {
            "date": date,
            "julian_day": julian_day,
            "julian_century": julian_century,
            "geom_mean_long_sun": geom_mean_long_sun,
            "geom_mean_anom_sun": geom_mean_anom_sun,
            "eccent_earth_orbit": eccent_earth_orbit,
            "sun_eq_of_ctr": sun_eq_of_ctr,
            "sun_true_long": sun_true_long,
            "sun_true_anom": sun_true_anom,
            "sun_rad_vector": sun_rad_vector,
            "sun_app_long": sun_app_long,
            "mean_oblic_ecliptic": mean_oblic_ecliptic,
            "obliq_corr": obliq_corr,
            "sun_rt_ascen": sun_rt_ascen,
            "sun_declin": sun_declin,
            "var_gamma": var_gamma,
            "eq_of_time": eq_of_time,
            "ha_sunrise": ha_sunrise,
            "solar_noon": solar_noon,
            "sunrise_time": sunrise_time,
            "sunset_time": sunset_time,
            "sunlight_duartion": sunlight_duration,
            "true_solar_time": true_solar_time,
            "hour_angle": hour_angle,
            "solar_zenith_angle": solar_zenith_angle,
            "solar_elevation_angle": solar_elevation_angle,
            "approx_atmospheric_refraction": approx_atmospheric_refraction,
            "solar_elevation_corrected_for_atm_refraction": solar_elevation_corrected_for_atm_refraction,
            "solar_azimut_angle": solar_azimuth_angle,
            "solar_zenith_corrected_for_atm_refraction": solar_zenith_corrected_for_atm_refraction,
        }
    )


def print_solar_geometry(dic: ee.Dictionary):
    dic = dic.getInfo()
    print(
        ee.Date(dic.get("date")["value"])
        .format(timeZone="America/Sao_Paulo")
        .getInfo(),
        # dic.get("julian_day"),
        # dic.get("julian_century"),
        # dic.get("geom_mean_long_sun"),
        # dic.get("geom_mean_anom_sun"),
        # dic.get("eccent_earth_orbit"),
        # dic.get("sun_eq_of_ctr"),
        # dic.get("sun_true_long"),
        # dic.get("sun_true_anom"),
        # dic.get("sun_rad_vector"),
        # dic.get("sun_app_long"),
        # dic.get("mean_oblic_ecliptic"),
        # dic.get("obliq_corr"),
        # dic.get("sun_rt_ascen"),
        # dic.get("sun_declin"),
        # dic.get("var_gamma"),
        # dic.get("eq_of_time"),
        # dic.get("ha_sunrise"),
        # ee.Date(dic.get("solar_noon")["value"])
        # .format(timeZone="America/Sao_Paulo")
        # .getInfo(),
        # ee.Date(dic.get("sunrise_time")["value"])
        # .format(timeZone="America/Sao_Paulo")
        # .getInfo(),
        # ee.Date(dic.get("sunset_time")["value"])
        # .format(timeZone="America/Sao_Paulo")
        # .getInfo(),
        # dic.get("sunlight_duartion"),
        # ee.Date(dic.get("true_solar_time")["value"]).format().getInfo(),
        # dic.get("hour_angle"),
        dic.get("solar_zenith_angle"),
        dic.get("solar_elevation_angle"),
        dic.get("approx_atmospheric_refraction"),
        dic.get("solar_elevation_corrected_for_atm_refraction"),
        dic.get("solar_azimut_angle"),
        dic.get("solar_zenith_corrected_for_atm_refraction"),
    )


def print_solar_geometry1(dic: ee.Dictionary):
    dic = dic.getInfo()
    print(
        ee.Date(dic.get("date")["value"])
        .format(timeZone="America/Sao_Paulo")
        .getInfo(),
        dic.get("zenith"),
        dic.get("azimuth"),
        dic.get("decl"),
        dic.get("eqtime"),
        dic.get("ha"),
    )
