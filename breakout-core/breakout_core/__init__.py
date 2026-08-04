"""breakout-core — the shared domain library.

Pure, ORM-free logic used by both Breakout Billing (the local tool) and the care
platform: the CPT catalog, money math, and superbill/statement PDF generation.
It depends only on the *shape* of the domain objects (see `domain.py` Protocols),
never on any particular database or web framework — so each product supplies its
own persistence and the logic stays identical across both.
"""
__version__ = "0.1.0"
