import ee

from cau_project.algorithms.config import BaseConfig


class BuildingHeightsConfig(BaseConfig, total=False):
    min_presence: float
    unmask_value: float | None


type BuilderConfig = BuildingHeightsConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "bh")
    min_presence: float = config.get("min_presence", 0.2)
    unmask_value: float | None = config.get("unmask_value", None)

    def building_heights(img: ee.Image) -> ee.Image:
        img_year = img.date().getRange("year")

        mosaic: ee.Image = (
            ee.ImageCollection("GOOGLE/Research/open-buildings-temporal/v1")
            .filterDate(img_year)
            .mosaic()
        )

        presence_mask = mosaic.select("building_presence").gte(min_presence)

        heights = (
            mosaic.select("building_height")
            .updateMask(presence_mask)
            .rename(output_band)
        )

        if unmask_value is not None:
            heights = heights.unmask(unmask_value)

        return img.addBands(heights)

    return building_heights


building_heights = _builder
