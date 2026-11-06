from typing import Literal

import ee

from cau_project.algorithms.config import BaseConfig


def mask_clouds_and_shadows(image: ee.Image) -> ee.Image:
    qa = image.select("QA_PIXEL")
    dilated_cloud = qa.bitwiseAnd(1 << 1).eq(0)
    cirrus_mask = qa.bitwiseAnd(1 << 2).eq(0)
    cloud_shadow_mask = qa.bitwiseAnd(1 << 3).eq(0)
    snow_mask = qa.bitwiseAnd(1 << 4).eq(0)
    cloud_mask = qa.bitwiseAnd(1 << 5).eq(0)

    mask = (
        dilated_cloud.And(cirrus_mask)
        .And(cloud_shadow_mask)
        .And(snow_mask)
        .And(cloud_mask)
    )
    return image.updateMask(mask)


def scale_to_temperature(image: ee.Image) -> ee.Image:
    lst_k = image.multiply(0.00341802).add(149.0)
    return lst_k


type LSTUnit = Literal["celsius", "kelvin"]


class LSTConfig(BaseConfig, total=False):
    unit: LSTUnit


type BuilderConfig = LSTConfig


def _builder(user_config: BuilderConfig | None = None):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "lst")
    unit: LSTUnit = config.get("unit", "celsius")

    l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
    landsat_collection = l8.merge(l9)

    season_dates = [(3, 20), (6, 20), (9, 22), (12, 21)]

    def lst(img: ee.Image) -> ee.Image:

        date = img.date()

        this_year = date.get("year")
        prev_year = this_year.subtract(1)
        next_year = this_year.add(1)

        years = [prev_year, this_year, next_year]

        whole_dates: ee.List = ee.List(
            [
                ee.Date.fromYMD(year, month, day)
                for year in years
                for month, day in season_dates
            ]
        )

        prev_date = ee.Date(
            whole_dates.filter(ee.Filter.lte("item", date)).reduce(ee.Reducer.max())
        )
        next_date = ee.Date(
            whole_dates.filter(ee.Filter.gt("item", date)).reduce(ee.Reducer.min())
        )

        lst_image: ee.Image = (
            landsat_collection.filterDate(prev_date, next_date)
            .map(mask_clouds_and_shadows)
            .map(lambda image: image.select("ST_B10"))
            .map(scale_to_temperature)
            .mean()
            .rename(output_band)
        )
        if unit == "celsius":
            lst_image = lst_image.subtract(273.15)

        return img.addBands(lst_image)

    return lst


lst = _builder
