import ee

from cau_project.algorithms.config import BaseConfig


class EmissivityConfig(BaseConfig, total=False):
    ndvi_band: str
    max_cloud_percentage: float


type BuilderConfig = EmissivityConfig


def mask_s2_scl(image: ee.Image) -> ee.Image:
    scl = image.select("SCL")
    bad = (
        scl.eq(0)
        .Or(scl.eq(1))
        .Or(scl.eq(3))
        .Or(scl.eq(8))
        .Or(scl.eq(9))
        .Or(scl.eq(10))
        .Or(scl.eq(11))
    )
    return image.updateMask(bad.Not())


def _builder(user_config: BuilderConfig | None = None):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "emissivity")
    ndvi_band: str = config.get("ndvi_band", "ndvi")
    max_cloud_percentage: float = config.get("max_cloud_percentage", 20.0)

    EPS_SOIL = 0.966
    EPS_VEG = 0.973
    EPS_WATER = 0.991
    NDVI_SOIL = 0.2
    NDVI_VEG = 0.5
    DELTA_EPS = 0.01

    def emissivity(img: ee.Image) -> ee.Image:
        ndvi = img.select(ndvi_band)

        s2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterDate(img.date().getRange("year"))
            .filterBounds(img.geometry())
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud_percentage))
            .map(mask_s2_scl)
        )
        s2_median = s2.median()

        # Água: MNDWI da composição (evita mediana de banda categórica)
        water = s2_median.normalizedDifference(["B3", "B11"]).gt(0)

        pv = ndvi.subtract(NDVI_SOIL).divide(NDVI_VEG - NDVI_SOIL).clamp(0, 1).pow(2)

        eps_mixed = (
            pv.multiply(EPS_VEG)
            .add(pv.multiply(-1).add(1).multiply(EPS_SOIL))
            .add(pv.multiply(pv.multiply(-1).add(1)).multiply(4 * DELTA_EPS))
        )

        eps = (
            eps_mixed.where(ndvi.lt(NDVI_SOIL), EPS_SOIL)
            .where(ndvi.gt(NDVI_VEG), EPS_VEG)
            .where(water, EPS_WATER)
            .rename(output_band)
        )

        return img.addBands(eps)

    return emissivity


emissivity = _builder
