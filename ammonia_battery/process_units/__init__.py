# ammonia_battery/process_units/__init__.py
"""
Process Units Module

Contains equipment classes and system integration for the ammonia battery.

Module initialization that imports all equipment and system classes, 
creating the bridge between equipment.py and systems.py.
"""

# NEW: Import statements to expose all classes
from .equipment import (
    # Utility functions
    adjust_cost_with_cepci,
    CEPCI_DICT,
    
    # Base class
    ProcessEquipment,
    
    # Power-to-Ammonia equipment
    H2ElectrolyserUnit,
    AirSeparationUnit,
    SynthesisLoop,
    
    # Storage equipment
    NH3Storage,
    
    # Ammonia-to-Power equipment
    AmmoniaToPowerBase,
    DirectNH3Combustion,
    BlendCombustion,
    H2Combustion
)

from .systems import (
    # System integration classes
    PowerToAmmonia,
    AmmoniaToPower,
    AmmoniaBattery
)

# NEW: Define what gets imported when someone does "from ammonia_battery.process_units import *"
__all__ = [
    # Utility functions
    'adjust_cost_with_cepci',
    'CEPCI_DICT',
    
    # Base class
    'ProcessEquipment',
    
    # Equipment classes
    'H2ElectrolyserUnit',
    'AirSeparationUnit', 
    'SynthesisLoop',
    'NH3Storage',
    'AmmoniaToPowerBase',
    'DirectNH3Combustion',
    'BlendCombustion',
    'H2Combustion',
    
    # System classes
    'PowerToAmmonia',
    'AmmoniaToPower',
    'AmmoniaBattery'
]