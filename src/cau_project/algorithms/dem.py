import ee

from cau_project.algorithms.config import BaseConfig


class DEMConfig(BaseConfig, total=False):
    pass


type BuilderConfig = DEMConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "dem")
    empty_image = ee.Image()

    def dem(img: ee.Image = empty_image):
        dem = (
            ee.Image("USGS/SRTMGL1_003")
            .rename(output_band)
            .resample("bicubic")
            .reproject(crs="EPSG:4326", scale=2)
        )

        return img.addBands(dem)

    return dem


dem = _builder


# dem_extrema = dem.reduceRegion(
#     reducer=ee.Reducer.minMax(),
#     geometry=region.geometry(),
#     scale=30,
#     maxPixels=int(1e9),
# )
#
# Map.add_layer(
#     ee_object=dem,
#     vis_params={
#         "min": dem_extrema.get("elevation_min"),
#         "max": dem_extrema.get("elevation_max"),
#         "palette": [
#             "#000080",
#             "#0000FF",
#             "#00FFFF",
#             "#FFFF00",
#             "#FF0000",
#         ],
#     },
#     name="Digital elevation model",
# )
