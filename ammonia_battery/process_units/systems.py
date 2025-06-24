"""
Integrated Battery System

Contains the NH3BatterySystem class that integrates all equipment
and provides the main interface for the optimization model


Contains system integration classes that combine multiple equipment 
units into complete systems (PowerToAmmonia, AmmoniaToPower, AmmoniaBattery)
"""

# Import statements to connect with equipment.py

from ammonia_battery.process_units.equipment import (
    H2ElectrolyserUnit, 
    AirSeparationUnit, 
    SynthesisLoop, 
    NH3Storage,
    DirectNH3Combustion,
    BlendCombustion,
    H2Combustion
)

class PowerToAmmonia:
    """
    Models the entire power-to-ammonia conversion chain
    
    Converts electrical energy to stored chemical energy in the form of ammonia (NH3)
    """
    def __init__(self, name, max_capacity):
        self.name = name
        self.max_capacity = max_capacity  # Total system capacity in MW
        self.max_daily_energy = max_capacity * 24 * 3600  # MJ/day
        self.lhv_NH3 = 18.6  # Energy stored in NH3 - MJ/kg NH3

        # Create electrolyser with updated scaling method and inflation adjustment
        self.electrolyser = H2ElectrolyserUnit(
            name=f"{name}_electrolyser",
            energy_consumption=35.3,  # MJ/kg NH3 35.3, 28.2, 24.9
            unit_capex=750000,  # $/MW 750000, 500000, 200000
            reference_capacity=10,  # 10 MW reference capacity
            stack_fraction=0.6,
            bop_fraction=0.4,
            bop_scaling_exponent=0.6,
            base_year=2024  # Assuming this is the base year for electrolyser costs
        )

        # Create air separation unit with new CAPEX equation and inflation adjustment
        self.air_separation_unit = AirSeparationUnit(
            name=f"{name}_asu",
            energy_consumption=0.74,  # MJ/kg NH3
            base_year=2010  # Base year for ASU correlation
        )

        # Create synthesis loop with inflation adjustment
        self.synthesis_loop = SynthesisLoop(
            name=f"{name}_synthesis_loop",
            h2_comp_energy=0.763,  # MJ/kg NH3 (from original H2 compressor)
            n2_comp_energy=0.587,  # MJ/kg NH3 (from original N2 compressor)
            reactor_energy=0.294,  # MJ/kg NH3 (from original NH3 reactor)
            base_year=2010  # Base year for synthesis loop correlation
        )

        self.components = [self.electrolyser, self.air_separation_unit, self.synthesis_loop]
        
        # Calculate efficiency and production rates at initialization
        self.total_energy_consumption, self.overall_efficiency = self.calc_p2a_efficiency()
        self.actual_daily_max_NH3_production = (self.max_daily_energy / self.total_energy_consumption) / 1000  # tonnes
        
        # Size equipment based on system capacity and production rates
        self.size_equipment()

    def calc_p2a_efficiency(self):
        """Calculate the overall energy efficiency of the P2A process"""
        # Total process energy consumption (MJ/kg NH3)
        total_energy_consumption = (
            self.electrolyser.energy_consumption + 
            self.air_separation_unit.energy_consumption +
            self.synthesis_loop.energy_consumption  # Combined energy consumption
        )
        
        # Overall process efficiency
        overall_efficiency = self.lhv_NH3 / total_energy_consumption
        
        return total_energy_consumption, overall_efficiency
    
    def size_equipment(self):
        """Size all equipment based on system capacity and production rates"""
        # Calculate power fractions for each component
        self.power_fractions = {
            self.electrolyser.name: self.electrolyser.energy_consumption / self.total_energy_consumption,
            self.air_separation_unit.name: self.air_separation_unit.energy_consumption / self.total_energy_consumption,
            self.synthesis_loop.name: self.synthesis_loop.energy_consumption / self.total_energy_consumption
        }

        # Size electrolyser based on power fraction (MW)
        self.electrolyser_power_MW = self.power_fractions[self.electrolyser.name] * self.max_capacity
        self.electrolyser.set_size(self.electrolyser_power_MW)
        
        # Size other components based on production rate (tonnes/day)
        self.air_separation_unit.set_size(self.actual_daily_max_NH3_production)
        self.synthesis_loop.set_size(self.actual_daily_max_NH3_production)

    def calculate_total_capex(self):
        """Calculate total capital expenditure using a generic component list."""
        capex_breakdown = {
            f"{comp.name}_capex": comp.sized_capex for comp in self.components
        }

        capex_breakdown['total_capex'] = sum(capex_breakdown.values())
        
        return capex_breakdown
    
    def calculate_annual_opex(self):
        return sum(comp.calculate_annual_opex() for comp in self.components)

class AmmoniaToPower:
    """
    Models the entire ammonia-to-power conversion chain
    
    Converts stored chemical energy in ammonia back to electrical energy
    """
    def __init__(self, name, max_capacity, conversion_technology="direct_combustion"):
        self.name = name
        self.max_capacity = max_capacity  # Total system capacity in MW
        self.lhv_NH3 = 18.6  # Energy stored in NH3 - MJ/kg NH3
        self.lhv_H2 = 120.1  # Energy stored in H2 - MJ/kg H2
        self.conversion_technology = conversion_technology
        
        # Initialize power generation with appropriate technology
        if conversion_technology == "direct_combustion":
            self.power_generation = DirectNH3Combustion(
                name=f"{name}_direct_combustion",
                efficiency=0.60,  # 60% efficiency
            )
        elif conversion_technology == "blend_combustion":
            self.power_generation = BlendCombustion(
                name=f"{name}_blend_combustion",
                efficiency=0.574,  # 57.4% efficiency
            )
        elif conversion_technology == "h2_combustion":
            self.power_generation = H2Combustion(
                name=f"{name}_h2_combustion",
                efficiency=0.525,  # 52.5% efficiency
            )
        else:
            raise ValueError(f"Unsupported conversion technology: {conversion_technology}")
        
        # Size the power generation equipment
        self.power_generation.set_size(max_capacity)

    def calculate_total_capex(self):
        """Calculate total capital expenditure for the ammonia-to-power system
        
        Returns:
            Dictionary containing the capital cost breakdown
        """
        # For AmmoniaToPower, there's only one main component - the power generation system
        # Check if we have component costs stored in the power generation object
        if hasattr(self.power_generation, 'ccgt_capex') and hasattr(self.power_generation, 'cracker_capex'):
            # For blend combustion and H2 combustion which have component costs
            capex_breakdown = {
                'ccgt_capex': self.power_generation.ccgt_capex,
                'cracker_capex': self.power_generation.cracker_capex,
                'total_capex': self.power_generation.sized_capex
            }
        else:
            # For direct combustion which doesn't have component costs
            capex_breakdown = {
                'total_capex': self.power_generation.sized_capex
            }
        
        return capex_breakdown
    
    def calculate_total_NH3_consumption(self):
        """Calculate daily NH3 consumption in tonnes/day based on max power capacity"""
        # Get hourly ammonia consumption in kg/hr
        hourly_NH3_consumption_kg = self.power_generation.calculate_ammonia_flow(self.max_capacity)
        
        # Convert to daily consumption in tonnes
        daily_NH3_consumption_tonnes = (hourly_NH3_consumption_kg * 24) / 1000
        
        return daily_NH3_consumption_tonnes
    
    def calculate_annual_opex(self):
        """Calculate annual operational expenditure for the ammonia-to-power system
        
        Returns:
            Annual OPEX in working currency (GBP)
        """
        # For AmmoniaToPower, the annual OPEX is simply the OPEX of the power generation component
        return self.power_generation.calculate_annual_opex()

class AmmoniaBattery:
    """
    Models a complete ammonia battery system
    
    Integrates Power-to-Ammonia, Storage, and Ammonia-to-Power systems
    """
    def __init__(self, name, p2a_capacity, storage_capacity, a2p_capacity, a2p_technology="direct_combustion"):
        self.name = name
        self.p2a = PowerToAmmonia(f"{name}_p2a", p2a_capacity)
        self.storage = NH3Storage(f"{name}_storage", storage_capacity)
        self.a2p = AmmoniaToPower(f"{name}_a2p", a2p_capacity, a2p_technology)
        self.subsystems = [self.p2a, self.storage, self.a2p]
    
    def calculate_total_system_costs(self):
        """Calculate the total CAPEX and OPEX of the entire system."""

        # Calculate individual components CAPEX
        p2a_capex = self.p2a.calculate_total_capex()['total_capex']
        storage_capex = self.storage.sized_capex
        a2p_capex = self.a2p.calculate_total_capex()['total_capex']
        
        # Calculate individual components OPEX
        p2a_opex = self.p2a.calculate_annual_opex()
        storage_opex = self.storage.calculate_annual_opex()
        a2p_opex = self.a2p.calculate_annual_opex()
        
        # Calculate totals
        total_capex = p2a_capex + storage_capex + a2p_capex
        total_opex = p2a_opex + storage_opex + a2p_opex
        
        # Return a dictionary with predictable, hardcoded keys
        return {
            'p2a_capex': p2a_capex,
            'storage_capex': storage_capex,
            'a2p_capex': a2p_capex,
            'total_capex': total_capex,
            'p2a_opex': p2a_opex,
            'storage_opex': storage_opex,
            'a2p_opex': a2p_opex,
            'total_opex': total_opex
        }