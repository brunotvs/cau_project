from typing import Literal

import ee

from cau_project.algorithms.config import BaseConfig

type RadiusUnits = Literal["meters", "pixels"]


class UrbanHeatIslandConfig(BaseConfig, total=False):
    lst_band: str
    urban_band: str
    radius: int
    scale: int
    geometry: ee.Geometry


type BuilderConfig = UrbanHeatIslandConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band: str = config.get("output_band", "heat_island_intensity")
    lst_band: str = config.get("lst_band", "lst")
    urban_band: str = config.get("urban_band", "urban")
    radius: int = config.get("radius", 5000)
    scale: int = config.get("scale", 30)
    geometry: ee.Geometry = config.get("geometry", ee.Geometry.BBox(-180, -90, 180, 90))

    def heat_island_intensity(img: ee.Image) -> ee.Image:
        lst: ee.Image = img.select(lst_band)
        urban: ee.Image = img.select(urban_band).unmask(0)
        lst_ref = lst.updateMask(urban.Not())

        patches = urban.selfMask().reduceToVectors(
            geometry=geometry, scale=scale, eightConnected=True, maxPixels=int(1e13)
        )

        def add_bra_mean(f: ee.Feature) -> ee.Element:
            ring = f.geometry().buffer(radius)
            mean = (
                lst_ref.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=ring,
                    scale=scale,
                    maxPixels=int(1e13),
                )
                .values()
                .get(0)
            )
            return f.set("bra_mean", mean)

        bra_mean_img = (
            patches.map(add_bra_mean)
            .filter(ee.Filter.notNull(["bra_mean"]))
            .reduceToImage(["bra_mean"], ee.Reducer.first())
        )

        hii = lst.subtract(bra_mean_img).updateMask(urban)
        hii = hii.rename(output_band)

        return img.addBands(hii)

    return heat_island_intensity


heat_island_intensity = _builder
