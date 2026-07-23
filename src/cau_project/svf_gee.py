import numpy as np
import math
import ee


def horizon_shift_vector(num_directions=16, radius_pixels=10, min_radius=1):
    shift = []

    angles = ee.List.sequence(0, num_directions - 1).map(
        lambda value: ee.Number(value).multiply(2 * math.pi / num_directions)
    )

    x = angles.map(lambda value: ee.Number(value).cos())
    y = angles.map(lambda value: ee.Number(value).sin())
    angles = angles.map(
        lambda value: ee.Number(value).multiply(10 * (180 / math.pi)).round().divide(10)
    )

    scale = 3
    radii = ee.List.sequence(0, (radius_pixels - min_radius) * scale + 1).map(
        lambda value: ee.Number(value).divide(scale).add(min_radius)
    )

    for i in range(num_directions):
        x_int = radii.map(lambda value: ee.Number(value).multiply(x.get(i)).round())
        y_int = radii.map(lambda value: ee.Number(value).multiply(y.get(i)).round())

        epsg_metric = "EPSG:3857"
        coords = (
            x_int.zip(y_int)
            .map(lambda coords: ee.Geometry.Point(ee.List(coords), epsg_metric))
            .distinct()
        )

        distances = coords.map(
            lambda point: ee.Geometry(point).distance(
                ee.Geometry.Point([0, 0], epsg_metric)
            )
        )

        shift.append(
            coords.map(lambda point: ee.Geometry(point).coordinates())
            .sort(distances)
            .zip(distances.sort())
        )

    return angles.zip(shift)


def sky_view_factor(image: ee.Image, num_dir=16):
    min_radius = 1

    move = horizon_shift_vector(num_dir)

    sample = image.sample(region=image.geometry(), geometries=True)
    print(sample.limit(5).getInfo())
