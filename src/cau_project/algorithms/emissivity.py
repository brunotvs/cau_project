import ee

from cau_project.algorithms.config import BaseConfig


def mask_clouds_and_shadows(image: ee.Image) -> ee.Image:
    qa = image.select("QA_PIXEL")
    dilated_cloud = qa.bitwiseAnd(1 << 1).eq(0)
    cirrus_mask = qa.bitwiseAnd(1 << 2).eq(0)
    cloud_shadow_mask = qa.bitwiseAnd(1 << 3).eq(0)
    snow_mask = qa.bitwiseAnd(1 << 4).eq(0)
    cloud_mask = qa.bitwiseAnd(1 << 5).eq(0)

    mask = (
        dilated_cloud.And(cirrus_mask)
        .And(cloud_shadow_mask)
        .And(snow_mask)
        .And(cloud_mask)
    )
    return image.updateMask(mask)


def scale(image: ee.Image) -> ee.Image:
    emis = image.multiply(0.0001).add(0)
    return emis


class EmissivityConfig(BaseConfig, total=False):
    pass


type BuilderConfig = EmissivityConfig


def _builder(user_config: BuilderConfig | None = None):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "emissivity")

    l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
    landsat_collection = l8.merge(l9)

    def emissivity(img: ee.Image) -> ee.Image:
        img_day = img.date().getRange("year")

        lst_image: ee.Image = (
            landsat_collection.filterDate(img_day)
            .map(mask_clouds_and_shadows)
            .map(lambda image: image.select("ST_EMIS"))
            .map(scale)
            .median()
            .rename(output_band)
        )

        return img.addBands(lst_image)

    return emissivity


emissivity = _builder
