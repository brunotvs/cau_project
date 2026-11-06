import ee

from cau_project.algorithms.config import BaseConfig


class UrbanConverConfig(BaseConfig, total=False):
    pass


type BuilderConfig = UrbanConverConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "urban")
    empty_image = ee.Image()

    def urban_area(img: ee.Image = empty_image):
        urban_area = (
            ee.ImageCollection("projects/mapbiomas-public/assets/brazil/lulc/v1")
            .mosaic()
            .eq(24)
            .rename(output_band)
        )

        urban_area = urban_area.updateMask(urban_area)

        return img.addBands(urban_area)

    return urban_area


urban_area = _builder
