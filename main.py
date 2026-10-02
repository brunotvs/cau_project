import datetime
import zoneinfo

import ee
import geemap.foliumap as geemap
import streamlit as st

import cau_project.algorithms as cau_algorithms
import cau_project.map as cau_map
import cau_project.palettes as cau_palettes
import cau_project.study_areas as cau_areas


def format_date(date: int, tz: int = 0) -> str:
    dt = datetime.datetime(
        1970,
        1,
        1,
        tzinfo=zoneinfo.ZoneInfo("America/Sao_Paulo"),
    ) + datetime.timedelta(milliseconds=date, hours=tz)

    return dt.strftime("%Y-%m-%d")


def solar_radiation(curr: ee.ComputedObject, prev: ee.ComputedObject):
    curr = ee.Image(curr)
    prev = ee.Image(prev)
    prev_date = prev.date()

    curr_date = curr.date()

    delta_seconds = curr_date.difference(prev_date, "second")

    return (
        curr.multiply(delta_seconds)
        .add(prev)
        .rename("radiation")
        .copyProperties(curr, ["system:time_start", "system:time_end"])
    )


st.set_page_config(layout="wide")
st.title("Interactive Earth Engine Dashboard")

ee.Initialize(project="earth-cau")

Map = geemap.Map(basemap="HYBRID")


region = (
    ee.FeatureCollection("FAO/GAUL/2025/level2")
    .filter(ee.Filter.eq("ADM1_NAME", "Sao Paulo"))
    .filter(ee.Filter.eq("ADM2_NAME", "Rio Grande Da Serra"))
)

region = ee.FeatureCollection(cau_areas.rgs)


regions = [
    ("jab", ee.FeatureCollection(cau_areas.jabaquara)),
    # ("sjc", ee.FeatureCollection(cau_areas.sjc)),
    # ("rgs", ee.FeatureCollection(cau_areas.rgs)),
]
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
mills_step = (
    start_date.advance(step_size, step_unit)
    .difference(start_date, "second")
    .multiply(1000)
)
dates = ee.List.sequence(start_date.millis(), end_date.millis(), mills_step)
dates = ee.List(
    [
        # ee.Date("2022-03-20T16:00:00-03:00").millis(),
        # ee.Date("2022-06-20T16:00:00-03:00").millis(),
        ee.Date("2023-09-22T16:00:00-03:00").millis(),
        # ee.Date("2023-12-21T16:00:00-03:00").millis(),
    ]
)


num_directions = 12
num_elevations = num_directions // 4
static_base = (
    ee.ImageCollection([ee.Image()])
    .map(
        lambda img: ee.Image(img).set(
            {
                "system:time_start": start_date.millis(),
            }
        )
    )
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
    .map(cau_algorithms.emissivity())
    .map(cau_algorithms.ndvi())
    .map(cau_algorithms.ruggedness({"height_band": "dsm"}))
    .map(cau_algorithms.averaged_building_height())
    .map(cau_algorithms.building_coverage_ratio())
    .map(cau_algorithms.building_volume_density({"radius": 200}))
    .map(cau_algorithms.area())
    .first()
)

print(static_base.bandNames().getInfo())


def process_time_step(current_date):
    current_date = ee.Date(current_date)
    return static_base.set("system:time_start", current_date.millis())


(
    ee.ImageCollection(dates.map(process_time_step))
    .filterBounds(region)
    .map(
        cau_algorithms.insolation(
            {"angular_precision": 1, "geometry": region.geometry()}
        )
    )
    .map(cau_algorithms.solar_power())
    .map(cau_algorithms.direct_irradiance())
    .map(cau_algorithms.diffuse_irradiance())
    .map(cau_algorithms.reflected_irradiance())
    .map(cau_algorithms.total_irradiance())
    .map(cau_algorithms.lst())
    # .aside(
    #     lambda col: [
    #         ee.ImageCollection(col)
    #         .filterDate(dates_list.get(i))
    #         .first()
    #         .aside(
    #             cau_map.add_layer_to_map(
    #                 {
    #                     "band": "total_irradiance",
    #                     "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #                     "palette": cau_palettes.qgis_reds,
    #                     "name": ee.Date(dates_list.get(i))
    #                     .format(timeZone="America/Sao_Paulo")
    #                     .getInfo()
    #                     or "svf",
    #                 }
    #             ),
    #             Map,
    #         )
    #         for i in range(dates_list.size().getInfo() or 0)
    #     ]
    # )
    .aside(
        lambda col: [
            ee.ImageCollection(col)
            .filterDate(ee.Date(date))
            .first()
            .aside(
                lambda img: [
                    geemap.ee_export_image_to_drive(
                        ee.Image(img).select(band).clip(region),
                        description=f"{region_name}-{band}-{format_date(date)}",
                        folder="export",
                        region=region.geometry(),
                        scale=4,
                        maxPixels=1e13,
                    )
                    for band in [
                        # "shadow",
                        # "shade",
                        # "total_irradiance",
                        # "svf",
                        # "ndvi",
                        # "ruggedness",
                        "bvd",
                        # "lst",
                        # "radiation"
                    ]
                    for region_name, region in regions
                ]
            )
            for date in dates.getInfo() or []
        ]
    )
    # .aside(
    #     lambda col: [
    #         ee.ImageCollection(col)
    #         .filterDate(ee.Date(date))
    #         .first()
    #         .aside(
    #             lambda img: [
    #                 cau_map.add_layer_to_map(
    #                     {
    #                         "band": "lst",
    #                         "min_max_strategy": cau_map.absolute_min_max(
    #                             region.geometry()
    #                         ),
    #                         "palette": cau_palettes.qgis_ylorrd,
    #                         "name": f"{region_name}-{band}-{format_date(date)}",
    #                     },
    #                 )(img.clip(region.geometry()), Map)
    #                 for band in [
    #                     # "shadow",
    #                     # "shade",
    #                     # "total_irradiance",
    #                     # "svf",
    #                     # "ndvi",
    #                     # "ruggedness",
    #                     # "bvd",
    #                     "lst",
    #                     # "radiation"
    #                 ]
    #                 for region_name, region in regions
    #             ]
    #         )
    #         for date in dates.getInfo() or []
    #     ]
    # )
    # NOTE: here
    # .aside(
    #     lambda col: [
    #         ee.ImageCollection(col)
    #         .filterDate(ee.Date(date))
    #         .first()
    #         .aside(
    #             lambda img: [
    #                 geemap.ee_export_image(
    #                     ee_object=img.select(band).clip(region.geometry()),
    #                     filename=f".export/{region_name}-{band}-{format_date(date)}.tif",
    #                     region=region.geometry(),
    #                     scale=10,
    #                 )
    #                 for band in [
    #                     # "shadow",
    #                     # "shade",
    #                     # "total_irradiance",
    #                     # "svf",
    #                     # "ndvi",
    #                     # "ruggedness",
    #                     "bvd",
    #                     # "lst",
    #                     # "radiation",
    #                 ]
    #                 for region_name, region in regions
    #             ]
    #         )
    #         for i, date in enumerate(dates.getInfo() or [])
    #     ]
    # )
    # .map(lambda img: img.clip(region))
    # .first()
    # .aside(
    #     lambda img: [
    #         cau_map.add_layer_to_map(
    #             {
    #                 "band": f"{band}",
    #                 "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #                 "palette": palette,
    #             }
    #         )(img, Map)
    #         for band, palette in [
    #             # ("shadow", cau_palettes.qgis_greys),
    #             # ("shade", cau_palettes.qgis_greys),
    #             # ("total_irradiance", cau_palettes.qgis_reds),
    #             # ("svf", cau_palettes.qgis_greys),
    #             # (
    #             #     "ndvi",
    #             #     cau_palettes.qgis_rdylbu[:-1][::-1] + cau_palettes.qgis_rdylgn,
    #             # ),
    #             # ("ruggedness", cau_palettes.qgis_terrain),
    #             ("abh", cau_palettes.qgis_terrain),
    #             # ("bcr", cau_palettes.qgis_terrain),
    #             # ("bvd", cau_palettes.qgis_terrain),
    #             # ("lst", cau_palettes.qgis_ylorrd),
    #             # ("radiation", cau_palettes.qgis_reds),
    #         ]
    #     ]
    # )
    # .map(lambda img: ee.Image(img).select("direct_irradiance"))
    # .iterate(
    #     solar_radiation,
    #     ee.Image(0).set(
    #         {
    #             "system:time_start": start_date.millis(),
    #         }
    #     ),
    # )
    # .aside(
    #     lambda img: print(
    #         ee.Image(img)
    #         .select("radiation")
    #         .reduceRegion(
    #             reducer=ee.Reducer.minMax(),
    #             geometry=region.geometry(),
    #             scale=4,
    #             bestEffort=True,
    #         )
    #         .getInfo()
    #     )
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "radiation",
    #             "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #             "palette": cau_palettes.qgis_reds,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     lambda img: [
    #         geemap.ee_export_image_to_drive(
    #             ee.Image(img).select(band).clip(region),
    #             description=f"{region_name}-{band}-2026-10-01",
    #             folder="export",
    #             region=region.geometry(),
    #             scale=4,
    #             maxPixels=1e13,
    #         )
    #         for band in [
    #             # "shadow",
    #             # "shade",
    #             # "total_irradiance",
    #             # "svf",
    #             # "ndvi",
    #             # "ruggedness",
    #             # "bvd",
    #             "lst",
    #             # "radiation"
    #         ]
    #         for region_name, region in regions
    #     ]
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "ndvi",
    #             "min_max_strategy": cau_map.arbitrary_min_max(0, 1),
    #             "palette": cau_palettes.qgis_rdylbu[:-1:-1] + cau_palettes.qgis_rdylgn,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "shade",
    #             "min_max_strategy": cau_map.arbitrary_min_max(0, 1),
    #             "palette": cau_palettes.qgis_greys,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "lst",
    #             "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #             "palette": cau_palettes.qgis_reds,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "svf",
    #             "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #             "palette": cau_palettes.qgis_reds,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "direct_irradiance",
    #             "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #             "palette": cau_palettes.qgis_reds,
    #         }
    #     ),
    #     Map,
    # )
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
    #             "band": "bvd",
    #             "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #             "palette": cau_palettes.qgis_terrain,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "albedo",
    #             "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #             "palette": cau_palettes.qgis_greys,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "emissivity",
    #             "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #             "palette": cau_palettes.qgis_greys,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "bh",
    #             "min_max_strategy": cau_map.absolute_min_max(region.geometry()),
    #             "palette": cau_palettes.qgis_terrain,
    #         }
    #     ),
    #     Map,
    # )
    # .aside(
    #     cau_map.add_layer_to_map(
    #         {
    #             "band": "lst",
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
