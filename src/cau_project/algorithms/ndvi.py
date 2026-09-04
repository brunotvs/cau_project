import ee

from cau_project.algorithms.config import BaseConfig


class NDVIConfig(BaseConfig, total=False):
    max_cloud_percentage: float


type BuilderConfig = NDVIConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "ndvi")
    max_cloud_percentage: float = config.get("max_cloud_percentage", 20.0)

    collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")

    def mask_s2_clouds(image: ee.Image) -> ee.Image:
        qa = image.select("QA60")

        cloud_bit_mask = 1 << 10
        cirrus_bit_mask = 1 << 11

        mask = (
            qa.bitwiseAnd(cloud_bit_mask)
            .eq(0)
            .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
        )

        return image.updateMask(mask)

    def ndvi(img: ee.Image) -> ee.Image:
        img_day = img.date().getRange("year")
        ndvi_layer = (
            collection.filterDate(img_day)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud_percentage))
            .map(mask_s2_clouds)
            .median()
            .normalizedDifference(["B8", "B4"])
            .rename(output_band)
        )

        return img.addBands(ndvi_layer)

    return ndvi


ndvi = _builder
