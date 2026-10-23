from __future__ import annotations

from fastmcp import FastMCP


# Create MCP server
mcp = FastMCP("arith")


def _as_number(x) -> float:
    """Convert input into a number."""
    
    # Accept int/float
    if isinstance(x, (int, float)):
        return float(x)

    # Accept numeric strings
    if isinstance(x, str):
        try:
            return float(x.strip())
        except ValueError:
            pass

    raise TypeError(
        "Expected a number (int/float or numeric string)"
    )


@mcp.tool()
async def add(a: float, b: float) -> float:
    """Return a + b."""
    return _as_number(a) + _as_number(b)


@mcp.tool()
async def subtract(a: float, b: float) -> float:
    """Return a - b."""
    return _as_number(a) - _as_number(b)


@mcp.tool()
async def multiply(a: float, b: float) -> float:
    """Return a * b."""
    return _as_number(a) * _as_number(b)


@mcp.tool()
async def divide(a: float, b: float) -> float:
    """Return a / b."""

    a = _as_number(a)
    b = _as_number(b)

    if b == 0:
        raise ValueError("Cannot divide by zero")

    return a / b


if __name__ == "__main__":
    mcp.run()