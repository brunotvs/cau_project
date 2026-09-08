import ee

from cau_project.algorithms.config import BaseConfig


class AlbedoConfig(BaseConfig, total=False):
    max_cloud_percentage: float


type BuilderConfig = AlbedoConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "albedo")
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

    def calculate_surface_albedo(image: ee.Image) -> ee.Image:
        scaled = image.select(["B2", "B4", "B8", "B11", "B12"]).divide(10000)
        albedo_expr = "((0.356 * blue) + (0.130 * red) + (0.373 * nir) + (0.085 * swir) + (0.072 * swir2) - 0.018) / 1.016"
        return scaled.expression(
            albedo_expr,
            {
                "blue": scaled.select("B2"),
                "red": scaled.select("B4"),
                "nir": scaled.select("B8"),
                "swir": scaled.select("B11"),
                "swir2": scaled.select("B12"),
            },
        ).rename("albedo")

    def albedo(img: ee.Image) -> ee.Image:
        img_date = img.date().getRange("year")

        albedo_layer = (
            collection.filterBounds(img.geometry())
            .filterDate(img_date)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud_percentage))
            .map(mask_s2_clouds)
            .map(calculate_surface_albedo)
            .median()
            .rename(output_band)
        )

        return img.addBands(albedo_layer)

    return albedo


albedo = _builder
