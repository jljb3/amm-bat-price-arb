import os
import pandas as pd
import numpy as np

def _get_timestep(df):
    """Calculates the time difference in hours between the first two rows."""
    if 'Time' not in df.columns or len(df) < 2:
        return 0.5 # Return a default if calculation isn't possible
    return (df['Time'].iloc[1] - df['Time'].iloc[0]).total_seconds() / 3600

def analyze_time_based_metrics(results_df):
    """
    Extracts time-based operation metrics from optimization results.
    This function now ONLY performs calculations and returns the results.
    """
    df = results_df.copy()
    
    if 'Time' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['Time']):
        df['Time'] = pd.to_datetime(df['Time'])

    df['hour'] = df['Time'].dt.hour
    df['day'] = df['Time'].dt.day
    df['month'] = df['Time'].dt.month
    df['season'] = pd.cut(
        df['Time'].dt.month,
        bins=[0, 3, 6, 9, 12],
        labels=['Winter', 'Spring', 'Summer', 'Fall']
    )

    timestep_hours = _get_timestep(df)
    
    monthly_operation = df.groupby('month').agg(
        charging_hours=('Is_Charging', lambda x: x.sum() * timestep_hours),
        discharging_hours=('Is_Discharging', lambda x: x.sum() * timestep_hours),
        idle_hours=('Is_Charging', lambda x: (len(x) - x.sum() - df.loc[x.index, 'Is_Discharging'].sum()) * timestep_hours)
    )

    hourly_by_season = df.groupby(['season', 'hour']).agg(
        avg_charging_power=('Charging_Power_MW', 'mean'),
        avg_discharging_power=('Discharging_Power_MW', 'mean'),
        charging_frequency=('Is_Charging', 'mean'),
        discharging_frequency=('Is_Discharging', 'mean')
    )

    df['prev_charging'] = df['Is_Charging'].shift(1).fillna(0)
    df['prev_discharging'] = df['Is_Discharging'].shift(1).fillna(0)
    df['start_charging'] = (df['Is_Charging'] == 1) & (df['prev_charging'] == 0)
    df['start_discharging'] = (df['Is_Discharging'] == 1) & (df['prev_discharging'] == 0)

    transitions = {
        'charging_cycles': df['start_charging'].sum(),
        'discharging_cycles': df['start_discharging'].sum(),
    }

    return {
        'monthly_operation': monthly_operation,
        'hourly_by_season': hourly_by_season,
        'transitions': transitions
    }

def analyze_operational_efficiency(results_df, max_capacity):
    """
    Extracts operational efficiency metrics from optimization results.
    This function now ONLY performs calculations and returns the results.
    """
    df = results_df.copy()
    
    if 'Time' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['Time']):
        df['Time'] = pd.to_datetime(df['Time'])

    timestep_hours = _get_timestep(df)
    df['capacity_utilization'] = df['NH3_Level_Tonnes'] / max_capacity

    monthly_utilization = df.groupby(df['Time'].dt.month).agg(
        avg_capacity_utilization=('capacity_utilization', 'mean'),
        max_capacity_utilization=('capacity_utilization', 'max'),
        min_capacity_utilization=('capacity_utilization', 'min')
    )

    utilization_bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
    df['utilization_bin'] = pd.cut(df['capacity_utilization'], bins=utilization_bins)
    
    storage_duration = df.groupby('utilization_bin').agg(
        hours=('TimeStep', lambda x: len(x) * timestep_hours),
        percentage_time=('TimeStep', lambda x: len(x) / len(df) * 100)
    )

    return {
        'monthly_utilization': monthly_utilization,
        'storage_duration': storage_duration,
        'summary': {
            'avg_utilization': df['capacity_utilization'].mean(),
            'max_storage_level': df['NH3_Level_Tonnes'].max(),
        }
    }

def calculate_summary_operational_metrics(results_df, p2a_capacity_mw, a2p_capacity_mw):
    """
    Calculates a high-level summary dictionary of key operational metrics.
    """
    if results_df.empty:
        return {} # Return empty dict if no data

    # Ensure 'Time' column is datetime for timestep calculation
    if 'Time' in results_df.columns and not pd.api.types.is_datetime64_any_dtype(results_df['Time']):
        results_df['Time'] = pd.to_datetime(results_df['Time'])
    
    timestep_hours = _get_timestep(results_df)
    time_fraction = (len(results_df) * timestep_hours) / (366 * 24)

    # Calculate annual hours
    annual_charging_hours = (results_df['Charging_Power_MW'] > 0).sum() * timestep_hours / time_fraction
    annual_discharging_hours = (results_df['Discharging_Power_MW'] > 0).sum() * timestep_hours / time_fraction

    # Calculate CAPEX utilization
    annual_energy_consumed = results_df['Charging_Power_MW'].sum() * timestep_hours / time_fraction
    annual_energy_produced = results_df['Discharging_Power_MW'].sum() * timestep_hours / time_fraction
    
    max_annual_consumption = p2a_capacity_mw * 366 * 24
    max_annual_production = a2p_capacity_mw * 366 * 24

    charging_capex_utilization = annual_energy_consumed / max_annual_consumption if max_annual_consumption > 0 else 0
    discharging_capex_utilization = annual_energy_produced / max_annual_production if max_annual_production > 0 else 0
    
    # Placeholder for a more detailed replacement calculation if needed
    num_electrolyser_replacements = int((annual_charging_hours * 25) // 80000)

    return {
        "annual_charging_hours": annual_charging_hours,
        "annual_discharging_hours": annual_discharging_hours,
        "charging_capex_utilization": charging_capex_utilization,
        "discharging_capex_utilization": discharging_capex_utilization,
        "num_electrolyser_replacements": num_electrolyser_replacements,
    }