"""Create the correct checker for one registry entry."""

from __future__ import annotations

from av1_monitor.checkers.averau import BuklyChecker
from av1_monitor.checkers.dibona import DibonaChecker
from av1_monitor.checkers.lavarella import BookingSuedtirolChecker
from av1_monitor.checkers.nuvolau import NuvolauChecker
from av1_monitor.checkers.scoiattoli import ScoiattoliChecker
from av1_monitor.checkers.tissi import PhpChecker
from av1_monitor.checkers.unsupported import UnsupportedChecker
from av1_monitor.registry import Accommodation


def create_checker(accommodation: Accommodation):
    factories = {
        "booking_suedtirol": BookingSuedtirolChecker,
        "bukly": BuklyChecker,
        "dibona": DibonaChecker,
        "nuvolau": NuvolauChecker,
        "php": PhpChecker,
        "scoiattoli": ScoiattoliChecker,
        "unsupported": UnsupportedChecker,
    }
    try:
        return factories[accommodation.adapter](accommodation)
    except KeyError as exc:
        raise ValueError(f"unknown adapter {accommodation.adapter!r}") from exc

