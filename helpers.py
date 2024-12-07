"""
Вспомогательные функции
"""

import webcolors
import numpy as np


def key_by_value(dictionary, value):
    for key, val in dictionary.items():
        if val == value:
            return key
    return None


def hex_to_name(color_hex):
    try:
        return webcolors.hex_to_name(color_hex)
    except ValueError:
        return color_hex  # если цвет не найден, просто возвращаем hex-код


def is_corner_hexagon(i, j, num_rings, ring):
    """Проверяем, является ли гексагон угловым."""
    return ring == (num_rings - 1) and (i, j) in [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0)]


def find_closest_edge(hexagon, point):
    x, y = point
    vertices = hexagon.get_xy()
    min_dist = float('inf')
    closest_edge_midpoint = (0, 0)

    for i in range(6):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % 6]

        # Вычисляем середину грани
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2

        dist = np.sqrt((x - mx) ** 2 + (y - my) ** 2)
        if dist < min_dist:
            min_dist = dist
            closest_edge_midpoint = (mx, my)

    return closest_edge_midpoint