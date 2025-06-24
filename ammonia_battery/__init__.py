# ammonia_battery/__init__.py
"""
Ammonia Battery Energy Storage System Package

A comprehensive package for modelling, optimising, and analysing 
ammonia battery energy storage systems.

Main package entry point that exposes the most commonly used classes 
(AmmoniaBattery, PowerToAmmonia, etc.) so users can simply from 
ammonia_battery import AmmoniaBattery.
"""

__version__ = "1.0.0"
__author__ = "Ammonia Battery Team"

# NEW: Import main components from process_units module
from .process_units import (
    # System classes (most commonly used)
    AmmoniaBattery,
    PowerToAmmonia,
    AmmoniaToPower,
    
    # Equipment classes
    H2ElectrolyserUnit,
    AirSeparationUnit,
    SynthesisLoop,
    NH3Storage,
    DirectNH3Combustion,
    BlendCombustion,
    H2Combustion,
    
    # Utility functions
    adjust_cost_with_cepci,
    CEPCI_DICT
)

# NEW: Define what gets imported when someone does "from ammonia_battery import *"
__all__ = [
    'AmmoniaBattery',
    'PowerToAmmonia', 
    'AmmoniaToPower',
    'H2ElectrolyserUnit',
    'AirSeparationUnit',
    'SynthesisLoop',
    'NH3Storage',
    'DirectNH3Combustion',
    'BlendCombustion',
    'H2Combustion',
    'adjust_cost_with_cepci',
    'CEPCI_DICT'
]