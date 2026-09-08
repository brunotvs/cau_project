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
    output_band: str = config.get("output_band", "dsm")
    dem_band: str = config.get("dem_band", "dem")
    bh_band: str = config.get("bh_band", "bh")

    def dsm(img: ee.Image) -> ee.Image:
        dem = img.select(dem_band)
        bh = img.select(bh_band).unmask(0)

        dsm_img = dem.add(bh).rename(output_band)
        return img.addBands(dsm_img)

    return dsm


dsm = _builder
