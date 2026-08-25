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
