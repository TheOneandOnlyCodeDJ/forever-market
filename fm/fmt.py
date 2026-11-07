"""Formatting layer: the only place copper becomes gold."""


def coin(copper):
    """Small amounts in readable units: 1234 -> '12.34s', 47 -> '47c'."""
    if copper is None:
        return "-"
    if copper >= 10000:
        return f"{copper / 10000:,.2f}g"
    if copper >= 100:
        return f"{copper / 100:.2f}s"
    return f"{copper:.0f}c"


def gold(copper):
    """1234567 -> '123.46g'. None and 0 (TSM's 'no data') render as '-'."""
    if not copper:
        return "-"
    return f"{copper / 10000:,.2f}g"


def pct(value):
    return "-" if value is None else f"{value:.1f}%"


def num(value):
    return "-" if value is None else str(value)
