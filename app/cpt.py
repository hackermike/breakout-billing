"""Compatibility shim — the CPT catalog now lives in the shared `breakout_core`
package. Import from here or from `breakout_core.cpt`; they are the same objects.
"""
from breakout_core.cpt import (
    BOOKABLE,
    BY_CODE,
    CPT_CODES,
    DEFAULT_CODE,
    Cpt,
    default_fee,
    description,
)

__all__ = [
    "BOOKABLE", "BY_CODE", "CPT_CODES", "DEFAULT_CODE", "Cpt",
    "default_fee", "description",
]
