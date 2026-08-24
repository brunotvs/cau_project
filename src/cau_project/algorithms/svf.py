import ee

from cau_project.algorithms.config import BaseConfig


class SkyViewFactorConfig(BaseConfig, total=False):
    dsm_band: str
    num_directions: int
    num_elevations: int


default_config: SkyViewFactorConfig = {"num_directions": 16, "num_elevations": 8}
type BuilderConfig = SkyViewFactorConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band = config.get("output_band", "svf")
    dsm_band: str = config.get("dsm_band", "dsm")
    num_directions: int = config.get("num_directions", 16)
    num_elevations: int = config.get("num_elevations", 8)

    def sky_view_factor(img: ee.Image):

        dsm = img.select(dsm_band)

        directions = ee.List.sequence(0, num_directions - 1).map(
            lambda value: ee.Number(value).multiply(360 / num_directions)
        )

        elevations = ee.List.sequence(0, num_elevations).map(
            lambda value: ee.Number(value).multiply(90 / num_elevations)
        )

        size1 = directions.size()
        size2 = elevations.size()
        total_size = size1.multiply(size2)

        def create_pair(index):
            i = ee.Number(index)
            idx1 = i.divide(size2).floor()
            idx2 = i.mod(size2)
            return ee.List([directions.get(idx1), elevations.get(idx2)])

        combinations = ee.List.sequence(0, total_size.subtract(1)).map(create_pair)

        svf = (
            (
                ee.ImageCollection.fromImages(
                    combinations.map(
                        lambda angles: (
                            ee.Terrain.hillShadow(
                                dsm,
                                ee.List(angles).get(0),
                                ee.List(angles).get(1),
                                neighborhoodSize=200,
                                hysteresis=True,
                            )
                            .Not()
                            .Not()
                        )
                    )
                )
                .sum()
                .divide(total_size)
            )
            .rename(output_band)
            .focalMean(radius=3, units="pixels")
        )

        return img.addBands(svf)

    return sky_view_factor


svf = _builder

# svf_extrema = svf.reduceRegion(
#     reducer=ee.Reducer.minMax(),
#     geometry=region.geometry(),
#     scale=30,
#     maxPixels=int(1e9),
#     tileScale=4,
# )
#
# Map.add_layer(
#     ee_object=svf,
#     vis_params={
#         "min": svf_extrema.get("shadow_min"),
#         "max": svf_extrema.get("shadow_max"),
#     },
#     name="SVF",
# )
