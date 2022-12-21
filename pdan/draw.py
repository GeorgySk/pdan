from functools import singledispatch

from gon.base import (Contour,
                      Geometry,
                      Multipoint,
                      Multipolygon,
                      Multisegment,
                      Point,
                      Polygon,
                      Segment)
from matplotlib import pyplot


@singledispatch
def draw(geometry: Geometry, *args, **kwargs) -> None:
    draw(geometry.point, *args, **kwargs)
    # raise TypeError(f"Got unexpected geometry type: {type(geometry)}")


@draw.register
def _(geometry: Multipoint, *args, **kwargs) -> None:
    for point in geometry.points:
        draw(point, *args, **kwargs)


@draw.register
def _(geometry: Point, *args, **kwargs) -> None:
    kwargs.setdefault('marker', 'o')
    pyplot.plot(*geometry, *args, **kwargs)


@draw.register
def _(geometry: Multisegment, *args, **kwargs) -> None:
    for segment in geometry.segments:
        draw(segment, *args, **kwargs)


@draw.register
def _(segment: Segment, *args, label: str = None, **kwargs):
    start, end = segment.start, segment.end
    draw(start, **({'color': kwargs['color']}
                   if 'color' in kwargs else {}))
    if label is not None:
        start_x, start_y = start.x, start.y
        end_x, end_y = end.x, end.y
        pyplot.text((start_x * 2 + end_x) / 3, (start_y * 2 + end_y) / 3,
                    label,
                    fontdict={'size': 20})
        pyplot.text(start_x, start_y, label,
                    fontdict={'size': 20})
    pyplot.plot((start.x, end.x), (start.y, end.y), *args, **kwargs)


@draw.register
def _(geometry: Contour, *args, fill: bool = False, **kwargs) -> None:
    xs = [point.x for point in geometry.vertices]
    ys = [point.y for point in geometry.vertices]
    xs = list(map(float, xs))
    ys = list(map(float, ys))
    if fill:
        pyplot.fill(xs, ys, *args, **kwargs)
    pyplot.plot(xs, ys, *args, **kwargs)


@draw.register
def _(geometry: Multipolygon, *args, **kwargs) -> None:
    for polygon in geometry.polygons:
        draw(polygon, *args, **kwargs)


@draw.register
def _(geometry: Polygon, *args, **kwargs) -> None:
    border, holes = geometry.border, geometry.holes
    draw(border, *args, **kwargs)
    kwargs.pop('color', None)
    kwargs.pop('fill', None)
    for hole in holes:
        draw(hole, *args, fill=True, color=(0, 0, 0, 0.1), **kwargs)


# @draw.register
# def _(geometry: 'Site', *args, **kwargs) -> None:
#     draw(geometry.location, *args, **kwargs)


def draw_multipoint(multipoint, *args, **kwargs):
    for point in multipoint:
        draw_point(point, *args, **kwargs)


def draw_point(point, *args, **kwargs):
    kwargs.setdefault('marker', 'o')
    pyplot.plot(*point, *args, **kwargs)


def draw_multisegment(multisegment, *args, **kwargs):
    for segment in multisegment:
        draw_segment(segment, *args, **kwargs)


def draw_segment(segment, *args, label: str = None, **kwargs):
    start, end = segment
    draw_point(start, **({'color': kwargs['color']}
                         if 'color' in kwargs else {}))
    if label is not None:
        start_x, start_y = start
        end_x, end_y = end
        pyplot.text((start_x * 2 + end_x) / 3, (start_y * 2 + end_y) / 3,
                    label,
                    fontdict={'size': 20})
        pyplot.text(start_x, start_y, label,
                    fontdict={'size': 20})
    pyplot.plot(*zip(start, end), *args, **kwargs)


def draw_multicontour(multicontour, *args, **kwargs):
    for contour in multicontour:
        draw_contour(contour, *args, **kwargs)


def draw_contour(contour, *args, fill: bool = False, **kwargs):
    xs, ys = zip(*(contour + contour[:1]))
    xs = list(map(float, xs))
    ys = list(map(float, ys))
    if fill:
        pyplot.fill(xs, ys, *args, **kwargs)
    pyplot.plot(xs, ys, *args, **kwargs)


def draw_multipolygon(multipolygon, *args, **kwargs):
    for polygon in multipolygon:
        draw_polygon(polygon, *args, **kwargs)


def draw_polygon(polygon, *args, **kwargs):
    border, holes = polygon
    draw_contour(border, *args, **kwargs)
    kwargs.pop('color', None)
    kwargs.pop('fill', None)
    for hole in holes:
        draw_contour(hole, *args, fill=True, color=(0, 0, 0, 0.1), **kwargs)


def draw_circle(center, radius, fill=False, **kwargs):
    ax = pyplot.gca()
    center_x, center_y = center
    ax.set_xlim((center_x - radius - 100,
                 center_x + radius + 100))
    ax.set_ylim(center_y - radius - 100,
                center_y + radius + 100)
    ax.add_artist(pyplot.Circle((center_x, center_y),
                                radius=radius,
                                fill=fill,
                                **kwargs))


def clf():
    pyplot.clf()


def show(block=False):
    pyplot.show(block=block)
