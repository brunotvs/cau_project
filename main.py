import ee
import geemap.foliumap as geemap
import streamlit as st

import cau_project.algorithms as cau_algorithms
import cau_project.map as cau_map
import cau_project.palettes as cau_palettes
import cau_project.study_areas as cau_areas

st.set_page_config(layout="wide")
st.title("Interactive Earth Engine Dashboard")

ee.Initialize(project="earth-cau")

Map = geemap.Map(basemap="HYBRID")


region = (
    ee.FeatureCollection("FAO/GAUL/2025/level2")
    .filter(ee.Filter.eq("ADM1_NAME", "Sao Paulo"))
    .filter(ee.Filter.eq("ADM2_NAME", "Rio Grande Da Serra"))
)

region = ee.FeatureCollection(cau_areas.sjc)
# south_america = ee.Geometry.Rectangle([-92, -56, -34, 13], geodesic=False)
# africa = ee.Geometry.Rectangle([-26, -35, 52, 38], geodesic=False)
# region = ee.FeatureCollection([ee.Feature(south_america), ee.Feature(africa)])

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


num_directions = 3
num_elevations = 3  # num_directions // 4
(
    ee.ImageCollection(dates_list.map(create_empty_image))
    .filterBounds(region)
    .map(cau_algorithms.dem())
    .map(cau_algorithms.building_height())
    .map(cau_algorithms.dsm())
    .map(cau_algorithms.walls({"threshold": 3}))
    .map(
        cau_algorithms.svf(
            {
                "num_directions": num_directions,
                "num_elevations": num_elevations,
            }
        )
    )
    .map(cau_algorithms.albedo())
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
    # .map(cau_algorithms.area())
    .map(
        cau_algorithms.insolation(
            {"angular_precision": 1, "geometry": region.geometry()}
        )
    )
    .map(cau_algorithms.solar_power({"zenith": 0}))
    .map(cau_algorithms.direct_irradiance())
    .map(cau_algorithms.diffuse_irradiance())
    .map(cau_algorithms.reflected_irradiance())
    .map(cau_algorithms.total_irradiance())
    .map(lambda img: img.clip(region))
    .first()
    .aside(
        cau_map.add_layer_to_map(
            {
                "band": "shadow",
                "min_max_strategy": cau_map.arbitrary_min_max(0, 1),
                "palette": cau_palettes.qgis_greys,
            }
        ),
        Map,
    )
    .aside(
        cau_map.add_layer_to_map(
            {
                "band": "shade",
                "min_max_strategy": cau_map.arbitrary_min_max(0, 1),
                "palette": cau_palettes.qgis_greys,
            }
        ),
        Map,
    )
    .aside(
        lambda img: Map.add_layer(
            ee.Image(img).visualize(
                bands="direct_irradiance",
                min=0,
                max=65,
                palette=cau_palettes.qgis_reds,
                forceRgbOutput=True,
            )
        )
    )
    .aside(
        lambda img: print(
            ee.Image(img.select("direct_irradiance"))
            .reduceRegion(
                reducer=ee.Reducer.minMax(),
                geometry=region.geometry(),
                scale=4,
                bestEffort=True,
            )
            .getInfo()
        )
    )
    .aside(
        cau_map.add_layer_to_map(
            {
                "band": "direct_irradiance",
                "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
                "palette": cau_palettes.qgis_reds,
            }
        ),
        Map,
    )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "diffuse_irradiance",
    #             "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #             "palette": cau_palettes.qgis_reds,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "reflected_irradiance",
    #             "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #             "palette": cau_palettes.qgis_reds,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "total_irradiance",
    #             "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #             "palette": cau_palettes.qgis_reds,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "ghi",
    #             "min_max_strategy": cau_map.arbitrary_min_max(0, 1100),
    #             "palette": cau_palettes.qgis_ylorrd,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "dni",
    #             "min_max_strategy": cau_map.arbitrary_min_max(0, 1100),
    #             "palette": cau_palettes.qgis_ylorrd,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "dhi",
    #             "min_max_strategy": cau_map.arbitrary_min_max(0, 1100),
    #             "palette": cau_palettes.qgis_ylorrd,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "area",
    #             "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #             "palette": cau_palettes.qgis_terrain,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(func2)
)


Map.to_streamlit(height=600)
