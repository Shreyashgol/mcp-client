from __future__ import annotations

import math
from typing import Literal

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="Local Math Server",
    instructions=(
        "Use these tools for arithmetic, powers, roots, and basic geometry "
        "calculations."
    ),
    log_level="ERROR",
)


def _require_non_negative(value: float, label: str) -> None:
    if value < 0:
        raise ValueError(f"{label} must be non-negative.")


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract the second number from the first."""
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide one number by another."""
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b


@mcp.tool()
def power(base: float, exponent: float) -> float:
    """Raise a base to a power."""
    return base**exponent


@mcp.tool()
def square_root(value: float) -> float:
    """Calculate a square root."""
    _require_non_negative(value, "value")
    return math.sqrt(value)


@mcp.tool()
def circle_area(radius: float) -> float:
    """Calculate the area of a circle."""
    _require_non_negative(radius, "radius")
    return math.pi * radius * radius


@mcp.tool()
def rectangle_area(width: float, height: float) -> float:
    """Calculate the area of a rectangle."""
    _require_non_negative(width, "width")
    _require_non_negative(height, "height")
    return width * height


@mcp.tool()
def triangle_area(base: float, height: float) -> float:
    """Calculate the area of a triangle."""
    _require_non_negative(base, "base")
    _require_non_negative(height, "height")
    return 0.5 * base * height


@mcp.tool()
def perimeter(
    shape: Literal["square", "rectangle", "triangle"],
    side_a: float,
    side_b: float | None = None,
    side_c: float | None = None,
) -> float:
    """Calculate a perimeter for a square, rectangle, or triangle."""
    _require_non_negative(side_a, "side_a")

    if shape == "square":
        return 4 * side_a

    if side_b is None:
        raise ValueError(f"{shape} requires side_b.")
    _require_non_negative(side_b, "side_b")

    if shape == "rectangle":
        return 2 * (side_a + side_b)

    if side_c is None:
        raise ValueError("triangle requires side_c.")
    _require_non_negative(side_c, "side_c")
    return side_a + side_b + side_c


if __name__ == "__main__":
    mcp.run("stdio")
