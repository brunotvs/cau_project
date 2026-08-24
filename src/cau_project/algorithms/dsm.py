import ee

from cau_project.algorithms.config import BaseConfig


class DSMConfig(BaseConfig, total=False):
    dem_band: str
    bh_band: str


type BuilderConfig = DSMConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band = config.get("output_band", "dsm")
    dem_band = config.get("dem_band", "dem")
    bh_band = config.get("bh_band", "bh")

    empty_image = ee.Image()

    def dsm(img: ee.Image = empty_image):
        dsm: ee.Image = img.expression(f'b("{dem_band}") + b("{bh_band}")').rename(
            output_band
        )

        return img.addBands(dsm)

    return dsm


dsm = _builder

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
