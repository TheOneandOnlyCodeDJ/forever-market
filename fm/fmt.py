"""Formatting layer: the only place copper becomes gold."""


def gold(copper):
    """1234567 -> '123.46g'. None and 0 (TSM's 'no data') render as '-'."""
    if not copper:
        return "-"
    return f"{copper / 10000:,.2f}g"


def pct(value):
    return "-" if value is None else f"{value:.1f}%"


def num(value):
    return "-" if value is None else str(value)
