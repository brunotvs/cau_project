import datetime
import math
import zoneinfo

import ee
import geemap.foliumap as geemap
import streamlit as st

import cau_project.algorithms as cau_algorithms
import cau_project.map as cau_map
import cau_project.palettes as cau_palettes
import cau_project.study_areas as cau_areas

# def compactness(img: ee.Image) -> ee.Image:
#         heights: ee.Image = img.select(height_band).unmask(0)
#
#         is_building = heights.gt(0)
#         pixel_area = ee.Image.pixelArea().multiply(is_building)
#
#         pixel_volume = heights.multiply(pixel_area)
#
#         gradients = heights.gradient()
#         grad_x = gradients.select("x")
#         grad_y = gradients.select("y")
#         facade_area_density = grad_x.hypot(grad_y).multiply(is_building)
#         facade_area = facade_area_density.multiply(scale)
#
#         total_surface_area = pixel_area.add(facade_area)
#
#         kernel = ee.Kernel.circle(radius=radius, units=radius_units)
#
#         neighborhood_volume = pixel_volume.reduceNeighborhood(
#             reducer=ee.Reducer.sum(),
#             kernel=kernel,
#         )
#
#         neighborhood_surface = total_surface_area.reduceNeighborhood(
#             reducer=ee.Reducer.sum(),
#             kernel=kernel,
#         )
#
#         factor = 36.0 * math.pi
#         compactness = (
#             neighborhood_volume.pow(2)
#             .multiply(factor)
#             .pow(1.0 / 3.0)
#             .divide(neighborhood_surface)
#             .where(neighborhood_surface.lte(0), 0)
#             .rename(output_band)
#         )
#
#         return img.addBands(compactness)


def func2(col):
    for i, date in enumerate(dates_list.getInfo() or []):
        (
            ee.ImageCollection(col)
            .filterDate(ee.Date(date["value"]))
            .map(
                lambda img: img.addBands(
                    wall_orientation_from_dsm(ee.Image(img.select("bh")).unmask(0), 1)
                )
            )
            .map(lambda img: img.clip(region))
            .first()
            .aside(
                cau_map.add_layer_to_map(
                    {
                        "band": "bh",
                        "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
                        "palette": cau_palettes.qgis_terrain,
                    }
                ),
                Map,
            )
            .aside(
                cau_map.add_layer_to_map(
                    {
                        "band": "wall_orientation",
                        "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
                        "palette": cau_palettes.qgis_terrain,
                        # + cau_palettes.qgis_spectral_r,
                    }
                ),
                Map,
            )
            .aside(
                lambda img: print(
                    img.select("wall_orientation")
                    .reduceRegion(
                        reducer=ee.Reducer.minMax().combine(
                            ee.Reducer.stdDev(), sharedInputs=True
                        ),
                        geometry=region,
                        scale=2,
                        maxPixels=1e9,
                    )
                    .getInfo()
                )
            )
            .aside(
                lambda img: print(
                    img.select("wall_orientation")
                    .reduceRegion(
                        reducer=ee.Reducer.histogram(
                            maxBuckets=36
                        ),  # buckets de 10 em 10 graus
                        geometry=region,
                        scale=2,
                        maxPixels=1e9,
                    )
                    .getInfo()
                )
            )
            # .aside(
            #     cau_map.add_layer_to_map(
            #         {
            #             "band": "shadow",
            #             "min_max_strategy": cau_map.arbitrary_min_max(0, 1),
            #             "name": f"shadow at {
            #                 datetime.datetime(
            #                     1970,
            #                     1,
            #                     1,
            #                     tzinfo=zoneinfo.ZoneInfo('America/Sao_Paulo'),
            #                 )
            #                 + datetime.timedelta(milliseconds=date['value'], hours=-3)
            #             }",
            #             "palette": cau_palettes.qgis_terrain,
            #         }
            #     ),
            #     Map,
            # )
        )


def func(col):
    for i, date in enumerate(dates_list.getInfo() or []):
        (
            ee.ImageCollection(col)
            .filterDate(ee.Date(date["value"]))
            .mosaic()
            .aside(
                cau_map.add_layer_to_map(
                    {
                        "band": "shadow",
                        "min_max_strategy": cau_map.arbitrary_min_max(0, 1),
                        "name": f"shadow at {
                            datetime.datetime(
                                1970,
                                1,
                                1,
                                tzinfo=zoneinfo.ZoneInfo('America/Sao_Paulo'),
                            )
                            + datetime.timedelta(milliseconds=date['value'], hours=-3)
                        }",
                        "palette": cau_palettes.gray,
                    }
                ),
                Map,
            )
        )


def wall_orientation_from_dsm(
    dsm_image: ee.Image,
    focal_radius_px=1,
):
    """Extrai a orientação (aspect) das paredes de edifícios a partir de um DSM.

    :param dsm_image: ee.Image do DSM (terreno + edificações)
    :param slope_threshold_deg: acima desse valor, o pixel é tratado como
        "parede". Precisa calibrar empiricamente (veja nota abaixo)
    :param focal_radius_px: raio (em pixels) de suavização leve antes do
        gradiente, pra reduzir ruído sem apagar a transição vertical
    :return: ee.Image com bandas 'wall_orientation' (graus, 0=N, sentido
        horário) e 'wall_slope' (graus), mascarada só nos pixels de parede
    """

    prec = 3

    dsm_multiplier = dsm_image.gt(0)
    dsm = dsm_image.divide(prec).floor().multiply(prec).updateMask(dsm_multiplier)

    focal_radius_px = 0
    dsm_smooth = (
        dsm.focalMean(radius=focal_radius_px, units="pixels")
        if focal_radius_px > 0
        else dsm
    ).unmask(0)

    grads = dsm_smooth.gradient()
    dz_dx = grads.select("x")
    dz_dy = grads.select("y")

    slope_deg = (
        dz_dx.pow(2)
        .add(dz_dy.pow(2))
        .sqrt()
        .atan()
        .multiply(180.0 / math.pi)
        .rename("wall_slope")
    )

    # Sinal já validado no seu teste anterior contra ee.Terrain.aspect()
    aspect_rad = ee.Image.atan2(dz_dx.multiply(-1), dz_dy.multiply(-1))
    aspect_deg = aspect_rad.multiply(180.0 / math.pi)
    aspect_deg = aspect_deg.where(aspect_deg.lt(0), aspect_deg.add(360))

    edges = ee.Image(ee.Algorithms.CannyEdgeDetector(dsm_smooth, prec, 1)).rename(
        "edges"
    )

    wall_orientation = aspect_deg.rename("wall_orientation").updateMask(edges)

    # return dsm_smooth.rename("wall_orientation")
    return ee.Image.cat([wall_orientation, slope_deg])


st.set_page_config(layout="wide")
st.title("Interactive Earth Engine Dashboard")

ee.Initialize(project="earth-cau")

Map = geemap.Map(basemap="HYBRID")


region = (
    ee.FeatureCollection("FAO/GAUL/2025/level2")
    .filter(ee.Filter.eq("ADM1_NAME", "Sao Paulo"))
    .filter(ee.Filter.eq("ADM2_NAME", "Rio Grande Da Serra"))
)

region = ee.FeatureCollection(cau_areas.jabaquara)
# region = ee.FeatureCollection(ee.Geometry.Point([-46.662374, -23.648771]).buffer(100))

Map.add_layer(
    ee_object=region.style(fillColor="0000", color="000F", width=5.0),
    vis_params={},
    name="First Level Administrative Units",
)


Map.center_object(region)

start_date = ee.Date("2023-01-01T16:00:00-03:00")
end_date = ee.Date("2023-01-01T16:00:00-03:00")


step_unit = "hour"
step_size = 1
n_dates = end_date.difference(start_date, step_unit).divide(step_size).floor()
dates_list = ee.List.sequence(0, n_dates).map(
    lambda d: start_date.advance(ee.Number(d).multiply(step_size), step_unit)
)

dates_list = ee.List([start_date])


def create_empty_image(current_date):
    current_date = ee.Date(current_date)
    return ee.Image(
        ee.Image.constant(0).set(
            {
                "system:time_start": current_date.millis(),
            }
        )
    )


num_directions = 64
num_elevations = num_directions // 4
(
    ee.ImageCollection(dates_list.map(create_empty_image))
    .filterBounds(region)
    .map(cau_algorithms.dem())
    .map(cau_algorithms.building_height())
    .map(cau_algorithms.dsm())
    # .map(
    #     cau_algorithms.svf(
    #         {
    #             "dsm_band": "dsm",
    #             "num_directions": num_directions,
    #             "num_elevations": num_elevations,
    #         }
    #     )
    # )
    # .map(cau_algorithms.albedo())
    # .map(cau_algorithms.ndvi())
    # .map(
    #     cau_algorithms.ruggedness(
    #         {"height_band": "dsm", "radius": 45, "radius_units": "meters"}
    #     )
    # )
    # .map(cau_algorithms.lst())
    # .map(cau_algorithms.averaged_building_height())
    # .map(cau_algorithms.building_coverage_ratio())
    # .map(cau_algorithms.building_volume_density())
    .map(
        cau_algorithms.insolation(
            {"angular_precision": 1, "geometry": region.geometry()}
        )
    )
    # .map(lambda img: img.clip(region))
    .aside(func2)
)


Map.to_streamlit(height=600)
