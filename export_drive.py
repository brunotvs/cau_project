import datetime
import zoneinfo
from pathlib import Path
from typing import Literal

import ee
import geemap.foliumap as geemap

import cau_project.algorithms as cau_algorithms
import cau_project.correlation as cau_correlation
import cau_project.study_areas as cau_areas

ee.Initialize(project="earth-cau")


def save_correlation(img, region, region_name):
    img = ee.Image(img)
    output_dir = Path(".export/correlation/")
    output_dir.mkdir(parents=True, exist_ok=True)

    date = img.date().format(format="YYYY-MM-dd", timeZone="America/Sao_Paulo")

    name = ee.String(f"{region_name}-sampcorr-").cat(date).getInfo() or ""
    print("saving:", name)

    cau_correlation.correlation_visualization(
        cau_correlation.sampled_correlation(img, region, scale=5, factor=0.01),
        figsize=(12, 10),
        rename_map={
            "heat_island_intensity": "HII",
        },
    ).savefig(output_dir / name, dpi=200)


def split_day_into_intevals(
    date: ee.Date | str | int,
    size: int,
    unit: Literal["year", "month", "week", "day", "hour", "minute", "second"],
) -> ee.List:
    date = ee.Date(date)
    day = date.getRange("day", timeZone="America/Sao_Paulo")

    interval_millis = (
        day.start()
        .advance(size, unit)
        .difference(day.start(), "seconds")
        .multiply(1000)
    )

    steps = ee.List.sequence(
        day.start().millis(), day.end().millis(), step=interval_millis
    )
    return steps


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
        .copyProperties(prev, ["system:time_start", "system:time_end"])
    )


def process_time_step(img: ee.Image):
    def process_time_step(current_date):
        current_date = ee.Date(current_date)
        return img.set("system:time_start", current_date.millis())

    return process_time_step


yearly_fixed = set()


def build_export_prefix(region_name: str, band: str):
    return f"{region_name}-{band}"


def set_yearly_fixed(img: ee.ComputedObject, region_name):
    img = ee.Image(img)
    bands = img.bandNames().remove("constant").getInfo() or []

    for band in bands:
        name = build_export_prefix(region_name, band)

        yearly_fixed.add(name)


exported_names = set()
exported_yearly_fixed = set()


def export_missing_bands(
    img: ee.ComputedObject, region: ee.FeatureCollection, region_name: str
):
    img = ee.Image(ee.Image(img).select(["radiation", "shadow"]))
    bands = img.bandNames().remove("constant").getInfo() or []
    date = (
        img.date().format(format="YYYY-MM-dd", timeZone="America/Sao_Paulo").getInfo()
    )

    for band in bands:
        name = build_export_prefix(region_name, band)
        if name in yearly_fixed:
            if name in exported_yearly_fixed:
                continue
        else:
            name = f"{name}-{date}"

        if name in exported_names:
            continue
        exported_names.add(name)

        geemap.ee_export_image_to_drive(
            image=img.select(band).clip(region),
            description=name,
            folder="export",
            scale=2,
            region=region.geometry(),
        )


def export_table(
    ee_object: ee.ComputedObject,
    region: ee.FeatureCollection,
    region_name: str,
    grid_size: int = 500,
):
    img: ee.Image = ee.Image(ee_object)

    date = img.date().format(format="YYYY-MM-dd", timeZone="America/Sao_Paulo")

    name = ee.String(f"{region_name}-").cat(date).getInfo()
    assert name is not None

    selected: ee.Image = img.select(img.bandNames().remove("constant"))
    grid = region.geometry().coveringGrid(
        proj=ee.Projection("EPSG:31983"), scale=grid_size
    )
    samples = selected.reduceRegions(
        collection=grid,
        reducer=ee.Reducer.mean().combine(
            reducer2=ee.Reducer.minMax(), sharedInputs=True
        ),
        scale=5,
        tileScale=16,
    )

    geemap.ee_export_vector_to_drive(
        collection=samples, description=name, folder="export-csv", fileFormat="csv"
    )


region = (
    ee.FeatureCollection("FAO/GAUL/2025/level2")
    .filter(ee.Filter.eq("GAUL1_NAME", "São Paulo"))
    .filter(ee.Filter.eq("GAUL2_NAME", "Rio Grande Da Serra"))
)


regions = [
    # ("jab", ee.FeatureCollection(cau_areas.jabaquara)),
    ("sjc", ee.FeatureCollection(cau_areas.sjc)),
    ("rgs", ee.FeatureCollection(cau_areas.rgs)),
]


years = ee.List(
    [
        ee.Date("2023-01-01T00:00:00-03:00").millis(),
    ]
)

days = [
    ee.List([ee.Date("2023-03-20T00:00:00-03:00").millis()]),
    ee.List([ee.Date("2023-06-20T00:00:00-03:00").millis()]),
    ee.List([ee.Date("2023-09-22T00:00:00-03:00").millis()]),
    ee.List([ee.Date("2023-12-21T00:00:00-03:00").millis()]),
]


num_directions = 2**5
num_elevations = num_directions // 4
[
    (
        ee.ImageCollection(years.map(process_time_step(ee.Image())))
        .map(cau_algorithms.dem())
        .map(cau_algorithms.urban_area())
        .map(cau_algorithms.building_height({"unmask_value": 0}))
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
        .map(cau_algorithms.ruggedness({"height_band": "dsm", "radius": 500}))
        .map(cau_algorithms.building_coverage_ratio({"radius": 500}))
        .map(cau_algorithms.building_volume_density({"radius": 500}))
        .map(cau_algorithms.averaged_building_height())
        .map(cau_algorithms.area())
        .map(lambda img: img.select(img.bandNames().remove("constant")))
        .first()
        # .aside(set_yearly_fixed, region_name)
        # .aside(export_missing_bands, region, region_name)
        .aside(
            lambda img: [
                (
                    ee.ImageCollection(day.map(process_time_step(img)))
                    .map(cau_algorithms.lst())
                    .map(
                        cau_algorithms.heat_island_intensity(
                            {"geometry": region.geometry()}
                        )
                    )
                    .first()
                    # .aside(export_missing_bands, region, region_name)
                    .aside(
                        lambda img: (
                            ee.ImageCollection(
                                split_day_into_intevals(
                                    ee.Image(img).date(), 15, "minute"
                                ).map(process_time_step(img))
                            )
                            .map(
                                cau_algorithms.insolation(
                                    {
                                        "angular_precision": 1,
                                        "geometry": region.geometry(),
                                    }
                                )
                            )
                            .map(cau_algorithms.solar_power())
                            .map(cau_algorithms.direct_irradiance())
                            .map(cau_algorithms.diffuse_irradiance())
                            .map(cau_algorithms.reflected_irradiance())
                            .map(cau_algorithms.total_irradiance())
                            .aside(
                                lambda col: (
                                    ee.Image.cat(
                                        img,
                                        (
                                            ee.ImageCollection(col)
                                            .map(
                                                lambda img: ee.Image(img).select(
                                                    "shadow"
                                                )
                                            )
                                            .mean()
                                            .set(
                                                {
                                                    "system:time_start": ee.Image(img)
                                                    .date()
                                                    .getRange(
                                                        "day",
                                                        timeZone="America/Sao_Paulo",
                                                    )
                                                    .start()
                                                    .millis(),
                                                }
                                            )
                                        ),
                                        (
                                            ee.ImageCollection(col)
                                            .map(
                                                lambda img: ee.Image(img).select(
                                                    "total_irradiance"
                                                )
                                            )
                                            .iterate(
                                                solar_radiation,
                                                ee.Image(0).set(
                                                    {
                                                        "system:time_start": ee.Image(
                                                            img
                                                        )
                                                        .date()
                                                        .getRange(
                                                            "day",
                                                            timeZone="America/Sao_Paulo",
                                                        )
                                                        .start()
                                                        .millis(),
                                                    }
                                                ),
                                            )
                                        ),
                                    )
                                    .aside(export_missing_bands, region, region_name)
                                    .aside(export_table, region, region_name, 50)
                                    # .aside(save_correlation, region, region_name)
                                )
                            )
                        )
                    )
                )
                for day in days
            ]
        )
    )
    for region_name, region in regions
]
