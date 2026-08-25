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
