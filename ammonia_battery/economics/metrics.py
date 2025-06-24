import numpy as np
import pandas as pd

from ammonia_battery.process_units.equipment import NH3Storage

# Constants for financial calculations
LIFETIME_YEARS = 25
DISCOUNT_RATE = 0.07  # 7%
LHV_NH3 = 18.6  # MJ/kg

def calculate_annualized_cost(capex, lifetime=LIFETIME_YEARS, discount_rate=DISCOUNT_RATE):
    """Calculate annualized cost from CAPEX using the capital recovery factor"""
    # Capital Recovery Factor (CRF)
    crf = (discount_rate * (1 + discount_rate)**lifetime) / ((1 + discount_rate)**lifetime - 1)
    return capex * crf

def _get_timestep(operational_results):
    """Helper function to get the timestep from the results dataframe"""
    if 'Time' in operational_results.columns and len(operational_results['Time']) > 1:
        # Use the more robust pandas check for datetime type
        if not pd.api.types.is_datetime64_any_dtype(operational_results['Time']):
            operational_results['Time'] = pd.to_datetime(operational_results['Time'])
        return (operational_results['Time'].iloc[1] - operational_results['Time'].iloc[0]).total_seconds() / 3600
    # Fallback if 'Time' column is not available or has only one entry
    return operational_results['TimeStep'].iloc[1] - operational_results['TimeStep'].iloc[0] if len(operational_results) > 1 else 0.5

def _calculate_electrolyser_replacement_costs(operational_results, a2p_technology, electrolyser_total_capex, lifetime, discount_rate, time_fraction):
    """Calculate present value of electrolyser stack replacement costs."""
    if a2p_technology == "h2_combustion":
        replacement_hours = 60000
    elif a2p_technology in ["blend_combustion", "direct_combustion"]:
        replacement_hours = 80000
    else:
        return 0.0

    timestep = _get_timestep(operational_results)
    period_operating_hours = (operational_results['Charging_Power_MW'] > 0).sum() * timestep
    annual_operating_hours = period_operating_hours / time_fraction if time_fraction > 0 else 0
    
    if annual_operating_hours == 0:
        return 0.0

    total_operating_hours = annual_operating_hours * lifetime
    num_replacements = int(total_operating_hours // replacement_hours)
    stack_cost = electrolyser_total_capex * 0.6  # Stack is 60% of total cost

    pv_replacements = 0.0
    for replacement_num in range(1, num_replacements + 1):
        replacement_year = (replacement_num * replacement_hours) / annual_operating_hours
        if replacement_year <= lifetime:
            pv_replacement = stack_cost / ((1 + discount_rate) ** replacement_year)
            pv_replacements += pv_replacement

    return pv_replacements

def calculate_system_economics_with_optimal_storage(results_dict, system_costs):
    """
    Calculates the complete system economics using the optimal storage design.
    This is the authoritative function for the final economic tally.
    """
    # Extract the necessary dictionaries from the results
    optimal_design = results_dict['optimal_design']
    operational_profit = results_dict['economics']['period_operational_profit']
    period_hours = results_dict['economics']['period_hours']
    
    # Get values
    optimal_capacity = optimal_design['optimal_capacity_tonnes']
    
    temp_storage = NH3Storage(name="temp_optimal_storage", max_storage_capacity=optimal_capacity)
    storage_capex = temp_storage.sized_capex

    # Get component costs passed in from the optimizer's battery object
    p2a_capex = system_costs['p2a_capex']
    a2p_capex = system_costs['a2p_capex']

    total_capex = p2a_capex + storage_capex + a2p_capex

    # OPEX is 2% of CAPEX for each component
    p2a_opex = 0.02 * p2a_capex
    a2p_opex = 0.02 * a2p_capex
    storage_opex = 0.02 * storage_capex
    total_opex = p2a_opex + storage_opex + a2p_opex

    annualized_capex = calculate_annualized_cost(total_capex)

    time_fraction = period_hours / (366 * 24)
    annual_operational_profit = operational_profit / time_fraction if time_fraction > 0 else 0
    net_annual_profit = annual_operational_profit - annualized_capex - total_opex

    final_economics = {
        'optimal_storage_capex': storage_capex,
        'p2a_capex': p2a_capex,
        'a2p_capex': a2p_capex,
        'total_system_capex': total_capex,
        'annualized_capex': annualized_capex,
        'total_annual_opex': total_opex,
        'annual_operational_profit': annual_operational_profit,
        'net_annual_profit': net_annual_profit,
        'period_operational_profit': operational_profit,
        'period_hours': period_hours,
        'time_fraction': time_fraction
    }
    return final_economics


def calculate_levelized_cost(annual_output, capital_cost, annual_fixed_cost=0, 
                             annual_variable_cost=0, pv_replacement_costs=0, 
                             lifetime=LIFETIME_YEARS, discount_rate=DISCOUNT_RATE):
    """
    A generic function to calculate any Levelized Cost (LCOx).

    Args:
        annual_output (float): The physical output per year (e.g., MWh, tonnes).
        capital_cost (float): The initial total capital expenditure.
        annual_fixed_cost (float): Recurring annual fixed costs (e.g., OPEX).
        annual_variable_cost (float): Recurring annual variable costs (e.g., fuel, electricity).
        pv_replacement_costs (float): The pre-calculated present value of all intermittent replacements.
        lifetime (int): Project lifetime in years.
        discount_rate (float): The discount rate.

    Returns:
        float: The levelized cost per unit of output (e.g., £/MWh, £/tonne).
    """
    if annual_output == 0:
        return float('inf')

    # Present Value Factor for an annuity
    pvf = (1 - (1 + discount_rate)**(-lifetime)) / discount_rate

    # Calculate the present value of all costs
    pv_total_costs = (capital_cost + 
                      ((annual_fixed_cost + annual_variable_cost) * pvf) + 
                      pv_replacement_costs)

    # Calculate the total discounted output over the lifetime
    pv_total_output = annual_output * pvf

    # Levelized cost is the total discounted cost per unit of total discounted output
    levelized_cost = pv_total_costs / pv_total_output
    
    return levelized_cost

def calculate_lcoa(results_dict, a2p_technology, electrolyser_total_capex, annual_p2a_opex, lifetime=25, discount_rate=0.07):
    """Calculate LCOA by calling the generic levelized cost function."""
    operational_results = results_dict['operational_results']
    economics = results_dict['economics']
    
    # Gather all the specific inputs for LCOA
    timestep = _get_timestep(operational_results)
    time_fraction = len(operational_results) * timestep / (366 * 24)
    
    annual_production = operational_results['NH3_Produced_Tonnes'].sum() / time_fraction if time_fraction > 0 else 0
    annual_electricity_cost = operational_results['Charging_Cost'].sum() / time_fraction if time_fraction > 0 else 0
    p2a_capital_cost = economics['p2a_capex']
    pv_replacements = _calculate_electrolyser_replacement_costs(
        operational_results, a2p_technology, electrolyser_total_capex, lifetime, discount_rate, time_fraction
    )

    # Call the master function with the prepared inputs
    lcoa = calculate_levelized_cost(
        annual_output=annual_production,
        capital_cost=p2a_capital_cost,
        annual_fixed_cost=annual_p2a_opex,
        annual_variable_cost=annual_electricity_cost,
        pv_replacement_costs=pv_replacements,
        lifetime=lifetime,
        discount_rate=discount_rate
    )

    return {
        'lcoa_per_tonne': lcoa,
        'annual_production_tonnes': annual_production,
        'p2a_capital_cost': p2a_capital_cost,
        'electrolyser_replacement_pv': pv_replacements,
    }

def calculate_lcoe(results_dict, lcoa_results, annual_a2p_opex, lifetime=25, discount_rate=0.07):
    """Calculate LCOE by calling the generic levelized cost function."""
    operational_results = results_dict['operational_results']
    economics = results_dict['economics']
    
    # 1. Gather all the specific inputs for LCOE
    timestep = _get_timestep(operational_results)
    time_fraction = len(operational_results) * timestep / (366 * 24)

    # The "output" is the electricity generated annually
    annual_generation = operational_results['Discharging_Power_MW'].sum() * timestep / time_fraction if time_fraction > 0 else 0
    
    # The "variable cost" is the annual cost of the ammonia fuel
    annual_nh3_consumed = operational_results['NH3_Consumed_Tonnes'].sum() / time_fraction if time_fraction > 0 else 0
    annual_fuel_cost = annual_nh3_consumed * lcoa_results['lcoa_per_tonne']

    # The "capital cost" is only for the A2P power block
    a2p_capital_cost = economics['a2p_capex']

    # 2. Call the master function with the prepared inputs
    lcoe = calculate_levelized_cost(
        annual_output=annual_generation,
        capital_cost=a2p_capital_cost,
        annual_fixed_cost=annual_a2p_opex,
        annual_variable_cost=annual_fuel_cost,
        pv_replacement_costs=0,  # Replacements are part of LCOA (the fuel cost)
        lifetime=lifetime,
        discount_rate=discount_rate
    )
    
    return {
        'lcoe_per_mwh': lcoe,
        'annual_generation_mwh': annual_generation,
        'annual_fuel_cost': annual_fuel_cost,
    }

def calculate_lcos(results_dict, a2p_technology, electrolyser_total_capex, lifetime=25, discount_rate=0.07):
    """Calculate LCOS by calling the generic levelized cost function."""
    operational_results = results_dict['operational_results']
    economics = results_dict['economics']
    
    # 1. Gather all the specific inputs for LCOS
    timestep = _get_timestep(operational_results)
    time_fraction = economics.get('time_fraction', len(operational_results) * timestep / (366 * 24))

    # The "output" is the energy discharged annually
    annual_energy_discharged = operational_results['Discharging_Power_MW'].sum() * timestep / time_fraction if time_fraction > 0 else 0
    
    # The "capital cost" is for the entire system
    total_system_capex = economics['total_system_capex']

    # The "fixed cost" is the total annual OPEX for the whole system
    total_annual_opex = economics['total_annual_opex']
    
    # The "intermittent cost" is the electrolyser replacement
    pv_replacements = _calculate_electrolyser_replacement_costs(
        operational_results, a2p_technology, electrolyser_total_capex, lifetime, discount_rate, time_fraction
    )

    # 2. Call the master function with the prepared inputs
    lcos = calculate_levelized_cost(
        annual_output=annual_energy_discharged,
        capital_cost=total_system_capex,
        annual_fixed_cost=total_annual_opex,
        annual_variable_cost=0,  # Charging electricity cost is excluded from LCOS by convention
        pv_replacement_costs=pv_replacements,
        lifetime=lifetime,
        discount_rate=discount_rate
    )
    
    # Also calculate cycling for reporting
    optimal_design = results_dict['optimal_design']
    storage_energy_capacity = optimal_design['optimal_capacity_tonnes'] * 1000 * LHV_NH3 / 3600
    annual_cycles = annual_energy_discharged / storage_energy_capacity if storage_energy_capacity > 0 else 0

    return {
        'lcos_per_mwh': lcos,
        'annual_energy_discharged_mwh': annual_energy_discharged,
        'annual_cycles': annual_cycles,
    }