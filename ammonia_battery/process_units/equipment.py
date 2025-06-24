"""
Individual Equipment Classes

Contains the core equipment classes for the ammonia battery system:
- Electrolyzer
- Air Separation Unit (ASU)
- Haber-Bosch reactor
- NH3 Cracker
- CCGT

This codefile effectoively describes the sizing, costing, and Chemical Engineering Plant Cost Index (CEPCI)
inflation adjustment methods to define eahc proces unit
"""

import numpy as np

# CEPCI data - a rule of thumb is that you shuld not use more than 5 years back and if you do then state that
CEPCI_DICT = {
    2024: 799.1, 2023: 797.9, 2022: 816.0, 2021: 708.8, 2020: 596.2, 
    2019: 607.5, 2018: 603.1, 2017: 567.5, 2016: 541.7, 2015: 556.8, 
    2014: 576.1, 2013: 567.3, 2012: 584.6, 2011: 585.7, 2010: 550.8, 
    2009: 521.9, 2008: 575.4, 2007: 525.4, 2006: 499.6, 2005: 468.2, 
    2004: 444.2, 2003: 402.0, 2002: 395.6, 2001: 394.3
}

def adjust_cost_with_cepci(base_cost, base_year, target_year=2024):
    if base_year not in CEPCI_DICT or target_year not in CEPCI_DICT:
        raise ValueError(f"CEPCI data not available for year {base_year} or {target_year}")
    
    cepci_ratio = CEPCI_DICT[target_year] / CEPCI_DICT[base_year]
    return base_cost * cepci_ratio

class ProcessEquipment:
    """
    A base class for all process equipment.

    It defines the common interface and provides helper methods
    """
    # Currency conversion factors remain centralized here
    USD_TO_GBP = 0.75
    EUR_TO_GBP = 0.85

    def __init__(self, name, currency='USD'):
        self.name = name
        self.original_currency = currency
        self.currency = 'GBP'  # All final costs will be in GBP.
        
        # These will be calculated by the child classes
        self.sized_capex = None
        self.size = None

    def _convert_to_gbp(self, cost_in_original_currency):
        """Centralised helper to convert a given cost to GBP"""
        if self.original_currency == 'USD':
            return cost_in_original_currency * self.USD_TO_GBP
        if self.original_currency == 'EUR':
            return cost_in_original_currency * self.EUR_TO_GBP
        return cost_in_original_currency

    def set_size(self, size):
        """
        This method is a placeholder that MUST be implemented
        by each child class to define its specific sizing and costing logic.
        """
        raise NotImplementedError("Each subclass must implement its own set_size method.")

    def calculate_annual_opex(self):
        """Calculate annual OPEX as 2% of the total sized capital cost."""
        if self.sized_capex is None:
            raise ValueError(f"Equipment {self.name} must be sized before calculating OPEX")
        return 0.02 * self.sized_capex
    
# --- PowerToAmmonia Units ---

class H2ElectrolyserUnit(ProcessEquipment):
    """Models hydrogen production via electrolysis"""
    def __init__(self, name, energy_consumption, unit_capex=500000, reference_capacity=10, 
                 stack_fraction=0.6, bop_fraction=0.4, bop_scaling_exponent=0.6, 
                 base_year=2024, currency='USD'):
        super().__init__(name, currency)
        
        self.energy_consumption = energy_consumption
        self.lhv_H2 = 21.28
        self.efficiency = self.lhv_H2 / self.energy_consumption
        self.base_year = base_year

        # Store base costs in their original currency
        self.base_unit_capex = unit_capex
        self.reference_capacity = reference_capacity
        self.stack_fraction = stack_fraction
        self.bop_fraction = bop_fraction
        self.bop_scaling_exponent = bop_scaling_exponent
    
    def set_size(self, size):
        self.size = size
        
        # Adjust base unit cost for inflation
        inflated_unit_capex = adjust_cost_with_cepci(self.base_unit_capex, self.base_year)
        
        # Convert the unit capex to GBP using the helper
        inflated_unit_capex_gbp = self._convert_to_gbp(inflated_unit_capex)
        
        # Calculate component costs using the GBP value
        stack_unit_capex = inflated_unit_capex_gbp * self.stack_fraction
        bop_unit_capex = inflated_unit_capex_gbp * self.bop_fraction

        # Calculate final sized CAPEX based on scaling laws
        stack_cost = stack_unit_capex * size
        scaling_factor = (size / self.reference_capacity) ** (self.bop_scaling_exponent - 1)
        bop_cost = bop_unit_capex * size * scaling_factor
        
        self.sized_capex = stack_cost + bop_cost
        return self.sized_capex

class AirSeparationUnit(ProcessEquipment):
    """Models nitrogen production via air separation."""
    def __init__(self, name, energy_consumption, base_year=2010, currency='USD'):
        super().__init__(name, currency)
        self.energy_consumption = energy_consumption
        self.base_year = base_year
        self.coef_a = 1606000
        self.coef_b = -0.6249
        self.coef_c = 9318
        self.n2_to_nh3_ratio = 14.01 / 17.0034
    
    def set_size(self, nh3_capacity):
        self.size = nh3_capacity
        n2_capacity = nh3_capacity * self.n2_to_nh3_ratio
        
        # Calculate base total cost in original currency (USD)
        unit_capex_usd = self.coef_a * (n2_capacity ** self.coef_b) + self.coef_c
        total_capex_usd = unit_capex_usd * n2_capacity
        
        inflated_capex_usd = adjust_cost_with_cepci(total_capex_usd, self.base_year)
        
        self.sized_capex = self._convert_to_gbp(inflated_capex_usd)
            
        return self.sized_capex

class SynthesisLoop(ProcessEquipment):
    """Models the combined NH3 synthesis loop."""
    def __init__(self, name, h2_comp_energy, n2_comp_energy, reactor_energy, 
                 base_year=2010, currency='USD'):
        super().__init__(name, currency)
        self.base_year = base_year
        self.energy_consumption = h2_comp_energy + n2_comp_energy + reactor_energy
        self.coef_a = 23850000
        self.coef_b = -1.340
        self.coef_c = 173500
    
    def set_size(self, nh3_capacity):
        self.size = nh3_capacity
        
        # Calculate base total cost in original currency (USD)
        unit_capex_usd = self.coef_a * (nh3_capacity ** self.coef_b) + self.coef_c
        total_capex_usd = unit_capex_usd * nh3_capacity
        
        capex_usd = adjust_cost_with_cepci(total_capex_usd, self.base_year)
        
        self.sized_capex = self._convert_to_gbp(capex_usd)
            
        return self.sized_capex


# --- Storage Classes ---

class NH3Storage(ProcessEquipment):
    """Models ammonia storage using the six-tenths rule for cost scaling."""
    def __init__(self, name, max_storage_capacity, reference_capacity=25000, 
                 reference_cost=39000000, reference_currency='USD', scaling_exponent=None):
        # The __init__ is now simpler. It just calls the parent.
        super().__init__(name, reference_currency)
        
        # Store all the specific parameters for this class
        self.max_capacity = max_storage_capacity  # tonnes
        self.reference_capacity = reference_capacity
        self.reference_cost = reference_cost
        self.lhv_NH3 = 18.6  # MJ/kg

        # The cost for storage is not dependent on a later 'set_size' call,
        # so we can calculate it immediately.
        self._calculate_total_capex()

    def _calculate_total_capex(self):
        """Internal method to calculate the total storage cost."""
        # Determine appropriate scaling exponent based on capacity
        if self.max_capacity < 10000:
            scaling_exponent = 0.7
        else:
            scaling_exponent = 0.6
        
        # Calculate scaled cost in original currency
        scaled_cost = self.reference_cost * (self.max_capacity / self.reference_capacity)**scaling_exponent
        
        self.sized_capex = self._convert_to_gbp(scaled_cost)

    def set_size(self, size):
        """
        For storage, 'sizing' doesn't change the pre-calculated cost.
        We just set the size attribute for consistency.
        """
        self.size = size
        # The capex is already calculated in __init__
        return self.sized_capex
    
    def calculate_maximum_energy_stored(self):
        """Calculate the maximum energy that can be stored in MJ."""
        return self.max_capacity * 1000 * self.lhv_NH3  # kg * MJ/kg


# --- AmmoniaToPower Classes ---

class AmmoniaToPowerBase(ProcessEquipment):
    """Base class for ammonia-to-power technologies"""
    def __init__(self, name, efficiency, reference_capacity=1000, reference_ccgt_cost=766000,
                 base_year=2019, currency='USD'):
        super().__init__(name, currency)
        
        self.efficiency = efficiency
        self.reference_capacity = reference_capacity
        self.reference_ccgt_cost = reference_ccgt_cost
        self.base_year = base_year
        self.lhv_NH3 = 18.6
        self.cracker_conversion = 0.99
    
    def calculate_ammonia_flow(self, power_capacity):
        """Calculates ammonia flow rate required for a given power output."""
        thermal_input_mj_hr = (power_capacity / self.efficiency) * 3600
        ammonia_flow_kg_hr = thermal_input_mj_hr / self.lhv_NH3
        return ammonia_flow_kg_hr
    
    def calculate_cracker_cost(self, hydrogen_flow):
        """Calculates cracker CAPEX based on hydrogen flow rate."""
        if hydrogen_flow <= 0:
            return 0
        
        # CAPEX in MMUSD from the correlation
        cracker_capex_mmusd = 18.171 * (hydrogen_flow ** 0.7451)
        # We assume the base year for the cracker cost is the same as the CCGT
        cracker_capex_inflated = adjust_cost_with_cepci(cracker_capex_mmusd * 1_000_000, self.base_year)
        return cracker_capex_inflated

    def set_size(self, power_capacity):
        self.size = power_capacity
        
        # Calculate base CCGT cost in original currency (USD)
        reference_plant_cost_per_kw = self.reference_ccgt_cost
        reference_plant_total_cost = reference_plant_cost_per_kw * self.reference_capacity # Total cost in $
        
        # Apply scaling rule
        ccgt_cost_base = reference_plant_total_cost * (power_capacity / self.reference_capacity) ** 0.8
        
        # Adjust for inflation
        ccgt_cost_inflated = adjust_cost_with_cepci(ccgt_cost_base, self.base_year)

        # Calculate total cost (including cracker, handled by subclasses)
        total_cost_inflated = self.calculate_total_cost(power_capacity, ccgt_cost_inflated)
        
        self.sized_capex = self._convert_to_gbp(total_cost_inflated)
        
        return self.sized_capex

    def calculate_total_cost(self, power_capacity, ccgt_cost_inflated):
        """To be implemented by each specific combustion technology."""
        raise NotImplementedError("Subclasses must implement calculate_total_cost.")

class DirectNH3Combustion(AmmoniaToPowerBase):
    """Models direct ammonia combustion"""
    def __init__(self, name, efficiency=0.60, **kwargs):
        super().__init__(name, efficiency, **kwargs)
    
    def calculate_total_cost(self, power_capacity, ccgt_cost_inflated):
        # No cracker, so total cost is just the CCGT cost
        return ccgt_cost_inflated

class BlendCombustion(AmmoniaToPowerBase):
    """Models blend combustion of NH3 and H2"""
    def __init__(self, name, efficiency=0.574, **kwargs):
        super().__init__(name, efficiency, **kwargs)
        self.ammonia_to_cracker_fraction = 0.224
    
    def calculate_total_cost(self, power_capacity, ccgt_cost_inflated):
        # Calculate H2 flow needed for the blend
        total_ammonia_flow_kg_hr = self.calculate_ammonia_flow(power_capacity)
        ammonia_to_cracker_kg_hr = total_ammonia_flow_kg_hr * self.ammonia_to_cracker_fraction
        # Stoichiometry to get H2 production
        h2_kg_hr = ammonia_to_cracker_kg_hr * (3.0 * 1.008 * 2) / (2.0 * 17.031) * self.cracker_conversion
        h2_tonnes_hr = h2_kg_hr / 1000
        
        # Calculate cracker cost
        cracker_cost_inflated = self.calculate_cracker_cost(h2_tonnes_hr)
        
        return ccgt_cost_inflated + cracker_cost_inflated

class H2Combustion(AmmoniaToPowerBase):
    """Models pure hydrogen combustion after cracking all NH3."""
    def __init__(self, name, efficiency=0.525, **kwargs):
        super().__init__(name, efficiency, **kwargs)
        self.ammonia_to_cracker_fraction = 1.0

    def calculate_total_cost(self, power_capacity, ccgt_cost_inflated):
        # Calculate H2 flow from cracking all ammonia
        total_ammonia_flow_kg_hr = self.calculate_ammonia_flow(power_capacity)
        h2_kg_hr = total_ammonia_flow_kg_hr * (3.0 * 1.008 * 2) / (2.0 * 17.031) * self.cracker_conversion
        h2_tonnes_hr = h2_kg_hr / 1000

        # Calculate cracker cost
        cracker_cost_inflated = self.calculate_cracker_cost(h2_tonnes_hr)

        return ccgt_cost_inflated + cracker_cost_inflated