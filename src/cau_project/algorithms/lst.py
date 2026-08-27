import datetime
from typing import Any, Literal

import ee

from cau_project.algorithms.config import BaseConfig

type DateRange = tuple[
    datetime.datetime | ee.Date | int | str | Any,
    datetime.datetime | ee.Date | int | str | Any,
]


type LSTUnit = Literal["celsius", "kelvin"]


class LSTConfig(BaseConfig, total=False):
    date_range: DateRange
    output_band: str
    unit: LSTUnit


type BuilderConfig = LSTConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band = config.get("output_band", "lst")
    unit = config.get("unit", "celsius")

    date_range: DateRange = config.get(
        "date_range", (0, datetime.datetime.now(datetime.UTC))
    )

    empty_image = ee.Image()

    def mask_clouds(image: ee.Image) -> ee.Image:
        qa = image.select("QA_PIXEL")
        cloud_shadow_mask = qa.bitwiseAnd(1 << 3).eq(0)
        cloud_mask = qa.bitwiseAnd(1 << 5).eq(0)
        cirrus_mask = qa.bitwiseAnd(1 << 2).eq(0)
        mask = cloud_shadow_mask.And(cloud_mask).And(cirrus_mask)

        return image.updateMask(mask)

    def scale_temperature_units(image: ee.Image) -> ee.Image:
        lst_k = image.select("ST_B10").multiply(0.00341802).add(149.0)

        lst = lst_k.subtract(273.15) if unit == "celsius" else lst_k

        return lst

    def lst(img: ee.Image = empty_image) -> ee.Image:
        lst_composite: ee.Image = (
            ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
            .filterDate(*date_range)
            .map(mask_clouds)
            .map(scale_temperature_units)
            .median()
            .rename(output_band)
            # .convolve(ee.Kernel.gaussian(radius=1.5, sigma=1, units="pixels"))
            # .resample("bicubic")
        )

        return img.addBands(lst_composite)

    return lst


lst = _builder
