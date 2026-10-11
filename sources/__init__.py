"""Beemer source adapters.

Each module pulls one family of free, public data and writes it to data/market.db.
All network access goes through :mod:`sources.http`, which rate-limits per host,
caches immutable files on disk and stops early when a host refuses us (for example
NSE blocking a cloud IP). Nothing here logs in, solves captchas or evades blocks.
"""
