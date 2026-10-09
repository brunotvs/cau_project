import ee

from cau_project.algorithms.config import BaseConfig


class AveragedBuildingHeightConfig(BaseConfig, total=False):
    bvd_band: str
    bcr_band: str


type BuilderConfig = AveragedBuildingHeightConfig


def _builder(user_config: BuilderConfig | None = None):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "abh")
    bvd_band: str = config.get("bvd_band", "bvd")
    bcr_band: str = config.get("bcr_band", "bcr")

    def averaged_building_height(img: ee.Image) -> ee.Image:
        bvd = img.select(bvd_band)
        bcr = img.select(bcr_band)

        abh = bvd.divide(bcr).updateMask(bcr.gt(0)).rename(output_band)

        return img.addBands(abh)

    return averaged_building_height


averaged_building_height = _builder
