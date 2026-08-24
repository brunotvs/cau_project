import ee

from cau_project.algorithms.config import BaseConfig


class NDVIConfig(BaseConfig, total=False):
    pass


type BuilderConfig = NDVIConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band = config.get("output_band", "ndvi")

    empty_image = ee.Image()

    def ndvi(img: ee.Image = empty_image):
        region = img.geometry()
        ndvi: ee.Image = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(region)
            .filterMetadata("CLOUDY_PIXEL_PERCENTAGE", "less_than", 20)
            .filterDate("2025-01-01", "2025-12-31")
            .mosaic()
            .normalizedDifference(["B8", "B4"])
        ).rename(output_band)

        return img.addBands(ndvi)

    return ndvi


ndvi = _builder

# Map.add_layer(
#     ee_object=ndvi,
#     vis_params={
#         "min": -1,
#         "max": 1,
#         "palette": ["blue", "blue", "red", "yellow", "green"],
#     },
#     name="NDVI",
# )
