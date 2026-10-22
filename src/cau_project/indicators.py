from typing import Literal

import ee

import cau_project.algorithms as cau_algorithms
import cau_project.study_areas as cau_areas

ee.Initialize(project="earth-cau")


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


region = (
    ee.FeatureCollection("FAO/GAUL/2025/level2")
    .filter(ee.Filter.eq("GAUL1_NAME", "São Paulo"))
    .filter(ee.Filter.eq("GAUL2_NAME", "Rio Grande Da Serra"))
)


regions = [
    # ("jab", ee.FeatureCollection(cau_areas.jabaquara)),
    ("sjc", ee.FeatureCollection(cau_areas.sjc)),
    # ("rgs", ee.FeatureCollection(cau_areas.rgs)),
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


def yearly_constant(
    region: ee.Geometry, year: ee.Date, num_directions: int = 2**5, radius=500
) -> ee.Image:
    num_elevations = num_directions // 4

    years = ee.List(
        [
            year.millis(),
        ]
    )
    return (
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
        .map(cau_algorithms.ruggedness({"height_band": "dsm", "radius": radius}))
        .map(cau_algorithms.building_coverage_ratio({"radius": radius}))
        .map(cau_algorithms.building_volume_density({"radius": radius}))
        .map(cau_algorithms.averaged_building_height())
        .map(cau_algorithms.area())
        .map(lambda img: img.select(img.bandNames().remove("constant")))
        .first()
    )


def daily_constant(
    yearly_constant: ee.Image, geometry: ee.Geometry, day: ee.Date
) -> ee.Image:
    days = ee.List([day.millis()])

    return (
        ee.ImageCollection(days.map(process_time_step(yearly_constant)))
        .map(cau_algorithms.lst())
        .map(cau_algorithms.heat_island_intensity({"geometry": geometry}))
    )


def instant_constant(
    daily_constant: ee.Image, geometry: ee.Geometry, instants: ee.List
) -> ee.ImageCollection:
    return (
        ee.ImageCollection(instants.map(process_time_step(daily_constant)))
        .map(
            cau_algorithms.insolation(
                {
                    "angular_precision": 1,
                    "geometry": geometry,
                }
            )
        )
        .map(cau_algorithms.solar_power())
        .map(cau_algorithms.direct_irradiance())
        .map(cau_algorithms.diffuse_irradiance())
        .map(cau_algorithms.reflected_irradiance())
        .map(cau_algorithms.total_irradiance())
    )


def daily_constant_ext(daily_constant: ee.Image, instant_constant: ee.ImageCollection):
    return ee.Image.cat(
        daily_constant,
        (
            ee.ImageCollection(instant_constant)
            .map(lambda img: ee.Image(img).select("shadow"))
            .mean()
            .set(
                {
                    "system:time_start": ee.Image(daily_constant)
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
            ee.ImageCollection(instant_constant)
            .map(lambda img: ee.Image(img).select("total_irradiance"))
            .iterate(
                solar_radiation,
                ee.Image(0).set(
                    {
                        "system:time_start": ee.Image(daily_constant)
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


def indicators(
    geometry: ee.Geometry,
    day: ee.Date,
    num_directions: int,
    interval_size: int,
    interval_units: Literal["year", "month", "week", "day", "hour", "minute", "second"],
    radius: int = 500,
    yc: ee.Image | None = None,
):

    instants = split_day_into_intevals(day, 15, "hour")

    y = yc or yearly_constant(geometry, day, num_directions, radius)
    d = daily_constant(y, geometry, day)
    i = instant_constant(d, geometry, instants)

    d_ext = daily_constant_ext(d, i)

    return y, d_ext, i
