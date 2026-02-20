## `ezan/__init__.py`
"""
Ezan - Namaz vakitleri ve kıble hesaplama modülü.
"""

from __future__ import annotations
import warnings
from typing import List, Optional, Union, Any, Dict, Tuple, Callable

__version__ = "0.1.0
__author__ = "Mehmet Keçeci"
__license__ = "AGPL-3.0-or-later"
__copyright__ = "Copyright 2026 Mehmet Keçeci"
__email__ = "mkececi@yaani.com"

from ezan.ezan import (
    get_user_location_and_date,
    get_manual_input,
    calculate_astronomical_twilight,
    calculate_sun_event,
    calculate_solar_noon,
    calculate_dhuhr_time,
    calculate_shadow_altitude,
    calculate_asr_time,
    qibla_angle,
    calculate_qibla_time,
    print_prayer_times,
)

__all__ = [
    'get_user_location_and_date',
    'get_manual_input',
    'calculate_astronomical_twilight',
    'calculate_sun_event',
    'calculate_solar_noon',
    'calculate_dhuhr_time',
    'calculate_shadow_altitude',
    'calculate_asr_time',
    'qibla_angle',
    'calculate_qibla_time',
    'print_prayer_times',
]