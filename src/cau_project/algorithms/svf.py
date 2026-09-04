import math
from typing import TypedDict

import ee


def solar_geometry(date: ee.Date) -> ee.Image:
    doy = date.getRelative("day", "year").add(1)
    gamma = doy.subtract(1).multiply(2.0 * math.pi / 365.0).float()

    eqtime = (
        gamma.multiply(2)
        .cos()
        .multiply(-3.2)
        .add(gamma.sin().multiply(229.18))
        .subtract(gamma.cos().multiply(107.5))
        .subtract(gamma.multiply(2).sin().multiply(7.8))
    )

    decl = (
        ee.Image(0.006918)
        .subtract(gamma.cos().multiply(0.399912))
        .add(gamma.sin().multiply(0.070257))
        .subtract(gamma.multiply(2).cos().multiply(0.006758))
        .add(gamma.multiply(2).sin().multiply(0.000907))
    )

    lon_lat = ee.Image.pixelLonLat()
    lon = lon_lat.select("longitude")
    lat = lon_lat.select("latitude").multiply(math.pi / 180.0)

    hour_utc = ee.Number(date.get("hour")).add(
        ee.Number(date.get("minute")).divide(60.0)
    )
    tst = ee.Image(hour_utc).multiply(60.0).add(eqtime).add(lon.multiply(4.0))
    ha = tst.divide(4.0).subtract(180.0).multiply(math.pi / 180.0)

    cos_zenith = (
        lat.sin()
        .multiply(decl.sin())
        .add(lat.cos().multiply(decl.cos()).multiply(ha.cos()))
        .clamp(-1.0, 1.0)
    )
    zenith = cos_zenith.acos().multiply(180.0 / math.pi).rename("zenith")
    sin_zenith = zenith.sin()

    cos_azimuth = (
        lat.sin()
        .multiply(cos_zenith)
        .subtract(decl.sin())
        .divide(lat.cos().multiply(sin_zenith))
        .clamp(-1.0, 1.0)
    )
    azimuth = cos_azimuth.acos()
    azimuth = (
        azimuth.where(ha.gt(0), ee.Image(2.0 * math.pi).subtract(azimuth))
        .multiply(180.0 / math.pi)
        .rename("azimuth")
    )

    zenith.addBands(azimuth)

    return zenith


def build_hillshadow_lut(
    dem: ee.Image,
    azimuth_bins: list[float],
    zenith_bins: list[float],
    neighborhood_size: int = 100,
) -> dict[tuple[float, float], ee.Image]:
    lut = {}
    for az in azimuth_bins:
        for ze in zenith_bins:
            shadow = ee.Terrain.hillShadow(dem, az, ze, neighborhood_size, True).byte()
            lut[(az, ze)] = shadow
    return lut


def sample_lut_by_pixel_coordinates(
    lut: dict[tuple[float, float], ee.Image],
    zenith_img: ee.Image,
    azimuth_img: ee.Image,
    azimuth_bins: list[float],
    zenith_bins: list[float],
    az_step: float,
) -> ee.Image:
    selected_shadow = ee.Image(0).byte()
    half_step = az_step / 2.0
    daylight_mask = zenith_img.lt(90)

    for i, az in enumerate(azimuth_bins):
        if az == 0:
            az_mask = azimuth_img.gte(360.0 - half_step).Or(azimuth_img.lt(half_step))
        else:
            az_mask = azimuth_img.gte(az - half_step).And(
                azimuth_img.lt(az + half_step)
            )

        for j, ze in enumerate(zenith_bins):
            z_min = (zenith_bins[j - 1] + ze) / 2.0 if j > 0 else 0.0
            z_max = (
                (ze + zenith_bins[j + 1]) / 2.0 if j < len(zenith_bins) - 1 else 90.0
            )

            ze_mask = zenith_img.gte(z_min).And(zenith_img.lt(z_max))

            cell_active = az_mask.And(ze_mask).And(daylight_mask)

            shadow_tile = lut[(az, ze)]
            selected_shadow = selected_shadow.where(cell_active, shadow_tile)

    return selected_shadow.updateMask(daylight_mask)


def compute_daily_insolation_fraction(
    dem: ee.Image,
    date_str: str,
    time_step_minutes: int = 30,
    azimuth_step: float = 30.0,
    neighborhood_size: int = 100,
) -> ee.Image:
    azimuth_bins = [float(a) for a in range(0, 360, int(azimuth_step))]
    zenith_bins = [15.0, 30.0, 45.0, 60.0, 75.0, 85.0]

    lut = build_hillshadow_lut(
        dem=dem,
        azimuth_bins=azimuth_bins,
        zenith_bins=zenith_bins,
        neighborhood_size=neighborhood_size,
    )

    base_date = ee.Date(date_str)
    start_of_day = ee.Date.fromYMD(
        base_date.get("year"), base_date.get("month"), base_date.get("day")
    )

    minutes = ee.List.sequence(0, 1440 - time_step_minutes, time_step_minutes)

    def _step_processor(min_offset: ee.Number) -> ee.Image:
        current_time = start_of_day.advance(min_offset, "minute")
        geometry = solar_geometry(current_time)
        zenith_img, azimuth_img = (
            geometry.select("zenith"),
            geometry.select("azimuth"),
        )

        shadow_at_step = sample_lut_by_pixel_coordinates(
            lut=lut,
            zenith_img=zenith_img,
            azimuth_img=azimuth_img,
            azimuth_bins=azimuth_bins,
            zenith_bins=zenith_bins,
            az_step=azimuth_step,
        )
        return shadow_at_step.unmask(0.0).toFloat()

    all_steps = ee.ImageCollection(minutes.map(_step_processor))
    daily_fraction = all_steps.mean().rename("insolation_fraction")

    return daily_fraction


def calculate_shadow(sun_position):
    sun_position = ee.Dictionary(sun_position)

    azimuth = sun_position.get("azimuth")
    elevation = sun_position.get("elevation")

    image = sun_position.get("image")

    elev_rad = ee.Number(elevation).multiply(math.pi / 180)
    weight = elev_rad.cos()

    shadow = (
        ee.Terrain.hillShadow(image, azimuth, elevation)
        .set("weight", weight)
        .set("azimuth", azimuth)
        .set("elevation", elevation)
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

    directions = ee.List.sequence(0, num_directions - 1).map(
        lambda value: ee.Number(value).multiply(360 / num_directions)
    )

    elevations = ee.List.sequence(0, num_elevations - 1).map(
        lambda value: (
            ee.Number(value).multiply(90 / (num_elevations - 1))
            if num_elevations > 1
            else 90
        )
    )

    def sky_view_factor(img: ee.Image):

        dsm = img.select(dsm_band)

        sun_position = directions.map(
            lambda dir: elevations.map(
                lambda el: ee.Dictionary(
                    {"azimuth": dir, "elevation": el, "image": dsm}
                )
            )
        ).flatten()

        shadow_collection = ee.ImageCollection.fromImages(
            sun_position.map(calculate_shadow)
        )

        svf = (
            shadow_collection.map(
                lambda img: ee.Image(img).multiply(ee.Number(img.get("weight")))
            )
            .sum()
            .divide(ee.Number(shadow_collection.aggregate_sum("weight")))
            .rename(svf_band)
        )

        return img.addBands(svf)

    return sky_view_factor


svf = _builder

__all__ = ["svf"]
