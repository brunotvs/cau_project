import datetime
from typing import Any

import ee

from cau_project.algorithms.config import BaseConfig

type DateRange = tuple[
    datetime.datetime | ee.Date | int | str | Any,
    datetime.datetime | ee.Date | int | str | Any,
]


class AlbedoConfig(BaseConfig, total=False):
    date_range: DateRange


type BuilderConfig = AlbedoConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band = config.get("output_band", "albedo")
    date_range: DateRange = config.get(
        "date_range", (0, datetime.datetime.now(datetime.UTC))
    )

    empty_image = ee.Image()

    def albedo(img: ee.Image = empty_image):
        PIXEL_MAX = 10_000
        albedo: ee.Image = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterMetadata("CLOUDY_PIXEL_PERCENTAGE", "less_than", 20)
            .filterDate(*date_range)
            .map(
                lambda img: img.select(
                    ["B4", "B2", "B8", "B11", "B12"],
                ).unitScale(0, PIXEL_MAX)
            )
            .map(
                lambda img: img.expression(
                    # https://gis.stackexchange.com/questions/318690/performing-surface-albedo-calculation-using-landsat-7-and-google-earth-engine
                    "((0.356 * blue) + (0.130 * red) + (0.373 * nir) + (0.085 * swir) + (0.072 * swir2) - 0.018) / 1.016",
                    {
                        "red": img.select("B4"),
                        "blue": img.select("B2"),
                        "nir": img.select("B8"),
                        "swir": img.select("B11"),
                        "swir2": img.select("B12"),
                    },
                )
            )
            .median()
        ).rename(output_band)

        return img.addBands(albedo)

    return albedo


albedo = _builder
