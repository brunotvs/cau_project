import math
from typing import TypedDict

import ee


class BaseConfig(TypedDict, total=False):
    output_band: str


def calculate_shadow(sun_position: ee.ComputedObject) -> ee.Image:
    sun_position = ee.Feature(sun_position)
    azimuth: ee.Number = ee.Number(sun_position.get("azimuth"))
    zenith: ee.Number = ee.Number(sun_position.get("zenith"))
    dsm = ee.Image(sun_position.get("dsm"))

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
        .set("weight", weight)
        .set("azimuth", azimuth)
        .set("zenith", zenith)
    )

    return shadow
