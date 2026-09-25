import math
from typing import TypedDict

import ee


class BaseConfig(TypedDict, total=False):
    output_band: str


def calculate_shadow(sun_position: ee.ComputedObject) -> ee.Image:
    sun_position = ee.Feature(sun_position)
    azimuth: ee.Number = ee.Number(sun_position.get("azimuth"))
    zenith: ee.Number = ee.Number(sun_position.get("zenith"))
    bh = ee.Image(sun_position.get("building_heights"))
    dem = ee.Image(sun_position.get("dem"))

    dsm = bh.unmask(0).add(dem)

    weight = zenith.multiply(math.pi / 180.0).cos()

    shadow = ee.Image(
        ee.Image(
            ee.Algorithms.If(
                zenith.eq(0),
                ee.Image.constant(1),
                ee.Algorithms.If(
                    zenith.gte(90),
                    ee.Image.constant(0),
                    ee.Image(ee.Terrain.hillShadow(dsm, azimuth, zenith, 200)),
                ),
            )
        )
        .rename("shadow")
        .cast({"shadow": "byte"})
        .set({"weight": weight, "azimuth": azimuth, "zenith": zenith})
    )

    edges = ee.Image(ee.Algorithms.CannyEdgeDetector(bh, 2, 2)).rename("edges")

    vertical_shadow = get_vertical_wall_illumination_fraction(
        dem, bh, azimuth, zenith
    ).updateMask(edges)

    shadow = shadow.add(vertical_shadow.unmask(0))

    return shadow


def get_vertical_wall_illumination_fraction(
    dem: ee.Image,
    bh: ee.Image,
    azimuth_deg: ee.Number,
    zenith_deg: ee.Number,
    scale_m: float = 2,
    max_dist_m: float = 200,
):
    altitude_deg = ee.Number(90).subtract(zenith_deg)
    azimuth_rad = azimuth_deg.multiply(math.pi / 180)
    altitude_rad = altitude_deg.multiply(math.pi / 180)
    tan_alpha = altitude_rad.tan()

    dsm_abs = dem.add(bh)

    base_abs = dem
    canopy = dsm_abs

    steps = int(max_dist_m / scale_m)

    sin_az = azimuth_rad.sin()
    cos_az = azimuth_rad.cos()

    max_shadow_line = ee.Image(0)

    proj = dsm_abs.projection()

    for step in range(1, steps + 1):
        dist_m = step * scale_m

        dx_m = sin_az.multiply(dist_m)
        dy_m = cos_az.multiply(dist_m)

        dsm_obstaculo_abs = dsm_abs.translate(dx_m.multiply(-1), dy_m, "meters", proj)

        this_shadow_line = dsm_obstaculo_abs.subtract(tan_alpha.multiply(dist_m))

        this_shadow_line = this_shadow_line.updateMask(dsm_obstaculo_abs.gt(canopy))

        max_shadow_line = max_shadow_line.max(this_shadow_line.unmask(0))

    illuminated_height = canopy.subtract(base_abs.max(max_shadow_line)).max(0).min(bh)

    illuminated_fraction = illuminated_height.divide(bh).clamp(0, 1)

    return illuminated_fraction
