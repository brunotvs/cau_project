import math
from typing import Required

import ee

from .config import BaseConfig


class HillShadowConfig(BaseConfig, total=False):
    dem_band: str
    bh_band: str
    walls_band: str
    neighborhood_size: int
    azimuth: Required[float | ee.Number]
    zenith: Required[float | ee.Number]


type BuilderConfig = HillShadowConfig


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

    dsm = dem.add(bh)

    sin_az = azimuth_rad.sin()
    cos_az = azimuth_rad.cos()

    steps = int(max_dist_m / scale_m)

    proj = dsm.projection()

    def shadow_line(dist_m):
        obstacle = dsm.translate(
            sin_az.multiply(dist_m).multiply(-1),
            cos_az.multiply(dist_m),
            "meters",
            proj,
        )
        return (
            obstacle.subtract(tan_alpha.multiply(dist_m))
            .updateMask(obstacle.gt(dsm))
            .unmask(0)
            .rename("shadow")
        )

    max_shadow_line_decl = ee.ImageCollection.fromImages(
        ee.List.sequence(1, steps)
        .map(lambda step: ee.Number(step).multiply(scale_m))
        .map(shadow_line)
    ).max()

    illuminated_fraction_decl = (
        dsm.subtract(dem.max(max_shadow_line_decl))
        .max(0)
        .min(bh)
        .divide(bh)
        .clamp(0, 1)
    )

    # max_shadow_line = ee.Image(0)
    # for step in range(1, steps + 1):
    #     dist_m = step * scale_m
    #
    #     dx_m = sin_az.multiply(dist_m)
    #     dy_m = cos_az.multiply(dist_m)
    #
    #     obstacle_height = dsm.translate(dx_m.multiply(-1), dy_m, "meters", proj)
    #
    #     this_shadow_line = obstacle_height.subtract(tan_alpha.multiply(dist_m))
    #
    #     this_shadow_line = this_shadow_line.updateMask(obstacle_height.gt(dsm))
    #
    #     max_shadow_line = max_shadow_line.max(this_shadow_line.unmask(0))
    #
    # illuminated_height = dsm.subtract(dem.max(max_shadow_line)).max(0).min(bh)
    #
    # illuminated_fraction = illuminated_height.divide(bh).clamp(0, 1)

    return illuminated_fraction_decl  # .neq(illuminated_fraction)


def _builder(
    user_config: BuilderConfig | None = None,
):

    config: BuilderConfig = user_config or {"azimuth": 45, "zenith": 270}
    shadow_band = config.get("output_band", "svf")
    dem_band: str = config.get("dem_band", "dem")
    bh_band: str = config.get("bh_band", "bh")
    walls_band: str = config.get("walls_band", "walls")
    neighborhood_size: int | None = config.get("neighborhood_size")
    azimuth: ee.Number = ee.Number(config.get("azimuth"))
    zenith: ee.Number = ee.Number(config.get("zenith"))

    def hill_shadow(img: ee.Image):
        bh = img.select(bh_band).unmask(0)
        dem = img.select(dem_band)
        walls = img.select(walls_band)

        dsm = bh.unmask(0).add(dem)

        shadow = ee.Image(
            ee.Image(
                ee.Algorithms.If(
                    zenith.eq(0),
                    ee.Image.constant(1),
                    ee.Algorithms.If(
                        zenith.gte(90),
                        ee.Image.constant(0),
                        ee.Image(
                            ee.Terrain.hillShadow(
                                dsm, azimuth, zenith, neighborhood_size
                            )
                        )
                        .add(
                            get_vertical_wall_illumination_fraction(
                                dem, bh, azimuth, zenith
                            )
                            .updateMask(walls)
                            .unmask(0)
                        )
                        .clamp(0, 1),
                    ),
                )
            )
            .rename(shadow_band)
            .cast({"shadow": "float"})
        )

        return img.addBands(shadow)

    return hill_shadow


hill_shadow = _builder

__all__ = [
    "hill_shadow",
]
