"""
Draws the example images of the README.

Run it with ``python docs/images/draw.py``: it overwrites the SVG files
next to this script, which the README links to on the ``main`` branch.
"""

from collections.abc import Sequence
from fractions import Fraction
from pathlib import Path

from pdan import (
    Contour,
    Point,
    Polygon,
    RadicalSum,
    minimizing_decomposition,
    minimizing_split,
    perimeter,
)

DIRECTORY = Path(__file__).parent
PANEL_SIZE = 240
MARGIN = 16
CAPTION_HEIGHT = 36
COLORS = ["#4e79a7", "#f28e2b", "#59a14f", "#e15759", "#b07aa1",
          "#76b7b2", "#edc948"]
REST_COLOR = "#d9dde3"
TEXT_COLOR = "#1f2328"
BACKGROUND_COLOR = "#ffffff"

Panel = tuple[list[tuple[Contour, str, str]], str]


def part_perimeter(part: Contour, _rest: Contour) -> RadicalSum:
    """
    Returns the perimeter of the part being cut off.

    :param part: part being cut off
    :param _rest: rest of the polygon, ignored
    :return: exact perimeter of `part`.
    """
    return perimeter(part)


def to_centroid(contour: Contour) -> tuple[float, float]:
    """
    Returns the centroid of the polygon defined by the contour.

    :param contour: defines a polygon
    :return: coordinates of the centroid as floats.
    """
    vertices = contour.vertices
    doubled_area = x_sum = y_sum = 0.0
    for start, end in zip(vertices, [*vertices[1:], vertices[0]]):
        cross = float(start.x * end.y - end.x * start.y)
        doubled_area += cross
        x_sum += float(start.x + end.x) * cross
        y_sum += float(start.y + end.y) * cross
    return x_sum / (3 * doubled_area), y_sum / (3 * doubled_area)


def to_label(area: Fraction, total: Fraction) -> str:
    """
    Formats an area as a percentage of the total area.

    :param area: area of a part
    :param total: area of the whole polygon
    :return: percentage rounded to an integer.
    """
    return f"{round(100 * area / total)}%"


def draw_panel(parts: Sequence[tuple[Contour, str, str]],
               caption: str,
               bounds: tuple[float, float, float, float],
               offset: float) -> list[str]:
    """
    Draws the parts of a polygon with their labels and a caption.

    Fits `bounds` into a square panel shifted right by `offset`,
    with the y axis pointing up.

    :param parts: contours with their fill colors and labels
    :param caption: text below the polygon
    :param bounds: minimum and maximum x and y of the polygon
    :param offset: horizontal position of the panel
    :return: SVG elements.
    """
    min_x, min_y, max_x, max_y = bounds
    side = PANEL_SIZE - 2 * MARGIN
    scale = side / max(max_x - min_x, max_y - min_y)
    shift_x = offset + MARGIN + (side - scale * (max_x - min_x)) / 2
    shift_y = MARGIN + (side + scale * (max_y - min_y)) / 2

    def project(x: float, y: float) -> str:
        """
        Converts polygon coordinates into SVG coordinates.

        :param x: abscissa in polygon coordinates
        :param y: ordinate in polygon coordinates
        :return: SVG coordinates joined with a comma.
        """
        return (f"{shift_x + scale * (x - min_x):.2f},"
                f"{shift_y - scale * (y - min_y):.2f}")

    elements = []
    for contour, color, _ in parts:
        points = " ".join(project(float(vertex.x), float(vertex.y))
                          for vertex in contour.vertices)
        elements.append(f"<polygon points='{points}' fill='{color}' "
                        f"stroke='{BACKGROUND_COLOR}' stroke-width='2.5' "
                        "stroke-linejoin='round'/>")
    for contour, color, label in parts:
        x, y = project(*to_centroid(contour)).split(",")
        text_color = TEXT_COLOR if color == REST_COLOR else "#ffffff"
        elements.append(f"<text x='{x}' y='{y}' fill='{text_color}' "
                        "font-size='15' font-weight='600' "
                        "text-anchor='middle' dominant-baseline='central'>"
                        f"{label}</text>")
    elements.append(f"<text x='{offset + PANEL_SIZE / 2}' "
                    f"y='{PANEL_SIZE + CAPTION_HEIGHT / 2}' "
                    f"fill='{TEXT_COLOR}' font-size='14' "
                    "text-anchor='middle' dominant-baseline='central'>"
                    f"{caption}</text>")
    return elements


def write_figure(name: str, panels: Sequence[Panel]) -> None:
    """
    Writes panels with polygon parts side by side to an SVG file.

    :param name: file name without the extension
    :param panels: parts with their colors and labels, and a caption,
        for each panel
    :return: nothing.
    """
    width = PANEL_SIZE * len(panels)
    height = PANEL_SIZE + CAPTION_HEIGHT
    elements = [(f"<rect width='{width}' height='{height}' rx='12' "
                 f"fill='{BACKGROUND_COLOR}'/>")]
    for index, (parts, caption) in enumerate(panels):
        vertices = [vertex
                    for contour, _, _ in parts
                    for vertex in contour.vertices]
        xs = [float(vertex.x) for vertex in vertices]
        ys = [float(vertex.y) for vertex in vertices]
        elements.extend(draw_panel(parts, caption,
                                   (min(xs), min(ys), max(xs), max(ys)),
                                   index * PANEL_SIZE))
    body = "\n  ".join(elements)
    (DIRECTORY / f"{name}.svg").write_text(
        "<svg xmlns='http://www.w3.org/2000/svg' "
        f"width='{width}' height='{height}' "
        f"viewBox='0 0 {width} {height}' "
        "font-family='Helvetica, Arial, sans-serif'>\n"
        f"  {body}\n</svg>\n",
        encoding="utf-8"
    )


def decomposition_panel(contour: Contour,
                        requirements: Sequence[Fraction]) -> Panel:
    """
    Decomposes the polygon and returns its labeled parts.

    Uses the perimeter of the part being cut off as the key.

    :param contour: defines a convex polygon
    :param requirements: areas of the parts as fractions of the whole area
    :return: parts with their colors and labels, and a caption.
    """
    total = Polygon(contour).area
    parts = minimizing_decomposition(
        contour, [requirement * total for requirement in requirements],
        key=part_perimeter
    )
    return ([(part, color, to_label(Polygon(part).area, total))
             for part, color in zip(parts, COLORS)],
            f"{len(parts)} parts")


def split_panel(contour: Contour, requirement: Fraction) -> Panel:
    """
    Splits the polygon and returns both labeled parts.

    :param contour: defines a convex polygon
    :param requirement: area of the part as a fraction of the whole area
    :return: parts with their colors and labels, and a caption.
    """
    total = Polygon(contour).area
    part, rest = minimizing_split(contour, requirement * total,
                                  key=part_perimeter)
    return ([(part, COLORS[0], to_label(requirement * total, total)),
             (rest, REST_COLOR, "")],
            f"cut off {to_label(requirement * total, total)} of the area")


def main() -> None:
    """
    Draws all example images.

    :return: nothing.
    """
    heptagon = Contour([Point(0, 2), Point(3, 0), Point(9, 0), Point(12, 3),
                        Point(11, 8), Point(6, 10), Point(1, 7)])
    write_figure("split",
                 [split_panel(heptagon, requirement)
                  for requirement in (Fraction(15, 100), Fraction(30, 100),
                                      Fraction(50, 100))])
    pentagon = Contour([Point(0, 0), Point(10, 1), Point(12, 6),
                        Point(5, 9), Point(1, 6)])
    write_figure("decomposition",
                 [decomposition_panel(heptagon,
                                      [Fraction(30, 100), Fraction(25, 100),
                                       Fraction(20, 100), Fraction(15, 100),
                                       Fraction(10, 100)]),
                  decomposition_panel(pentagon, [Fraction(1, 4)] * 4),
                  decomposition_panel(heptagon, [Fraction(1, 7)] * 7)])


if __name__ == "__main__":
    main()
