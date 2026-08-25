import ee


from cau_project.algorithms.config import BaseConfig


class RuggednessConfig(BaseConfig, total=False):
    dem_band: str


type BuilderConfig = RuggednessConfig


def _builder(
    user_config: BuilderConfig | None = None,
):
    config: BuilderConfig = user_config or {}
    output_band = config.get("output_band", "ruggedness")
    dem_band = config.get("dem_band", "dem")

    empty_image = ee.Image()

    # Riley et al., 1999
    def ruggedness(img: ee.Image = empty_image):
        kernel = ee.Kernel.square(radius=1, units="pixels")

        dem = img.select(dem_band)
        sum_dem = dem.reduceNeighborhood(reducer=ee.Reducer.sum(), kernel=kernel)

        sum_dem_sq = dem.pow(2).reduceNeighborhood(
            reducer=ee.Reducer.sum(), kernel=kernel
        )

        valid_pixel_count = dem.mask().reduceNeighborhood(
            reducer=ee.Reducer.sum(), kernel=kernel
        )

        rugg = (
            sum_dem_sq.subtract(dem.multiply(sum_dem).multiply(2))
            .add(dem.pow(2).multiply(valid_pixel_count))
            .max(0)
            .sqrt()
            .rename(output_band)
        )

        return img.addBands(rugg)

    return ruggedness


ruggedness = _builder
