import datetime
from typing import Any

import ee

from cau_project.algorithms.config import BaseConfig

type DateRange = tuple[
    datetime.datetime | ee.Date | int | str | Any,
    datetime.datetime | ee.Date | int | str | Any,
]


class NDVIConfig(BaseConfig, total=False):
    date_range: DateRange


type BuilderConfig = NDVIConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band = config.get("output_band", "ndvi")

    date_range: DateRange = config.get(
        "date_range", (0, datetime.datetime.now(datetime.UTC))
    )

    empty_image = ee.Image()

    def ndvi(img: ee.Image = empty_image):
        ndvi: ee.Image = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterMetadata("CLOUDY_PIXEL_PERCENTAGE", "less_than", 20)
            .filterDate(*date_range)
            .mosaic()
            .normalizedDifference(["B8", "B4"])
        ).rename(output_band)

        return img.addBands(ndvi)

    return ndvi


ndvi = _builder
