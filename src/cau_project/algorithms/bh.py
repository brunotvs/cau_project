import datetime
from typing import Any

import ee

from cau_project.algorithms.config import BaseConfig

type DateRange = tuple[
    datetime.datetime | ee.Date | int | str | Any,
    datetime.datetime | ee.Date | int | str | Any,
]


class BuildingHeightsConfig(BaseConfig, total=False):
    date_range: DateRange


type BuilderConfig = BuildingHeightsConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "bh")
    date_range: DateRange = config.get(
        "date_range", (0, datetime.datetime.now(datetime.UTC))
    )
    empty_image = ee.Image()

    def building_heights(img: ee.Image = empty_image):
        heights: ee.Image = (
            ee.ImageCollection("GOOGLE/Research/open-buildings-temporal/v1")
            .select("building_height")
            .filterDate(*date_range)
            .mosaic()
        ).rename(output_band)

        return img.addBands(heights)

    return building_heights


building_heights = _builder


# height_extrema = heights.reduceRegion(
#     reducer=ee.Reducer.percentile([0, 100]).setOutputs(["min", "max"]),
#     geometry=region.geometry(),
#     scale=30,
#     maxPixels=int(1e9),
# )
#
# Map.add_layer(
#     ee_object=heights,
#     vis_params={
#         "min": 0,
#         "max": height_extrema.get("building_height_max"),
#         "palette": [
#             "#000080",
#             "#0000FF",
#             "#00FFFF",
#             "#FFFF00",
#             "#FF0000",
#         ],
#     },
#     name="Building Heights (m)",
# )
