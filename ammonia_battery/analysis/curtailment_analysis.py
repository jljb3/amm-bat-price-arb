import pandas as pd
import numpy as np

def analyze_curtailment_interactions(optimization_results_df, timestep_hours=0.5):
    """
    Analyzes how the battery interacts with curtailment periods.
    This is a pure calculation function.
    """
    df = optimization_results_df.copy()
    
    # Identify different operational states
    df['Is_Curtailment'] = df['Curtailment'] > 0
    df['Is_Battery_Charging'] = df['Charging_Power_MW'] > 0
    df['Is_Battery_Discharging'] = df['Discharging_Power_MW'] > 0
    df['Is_Battery_Idle'] = (df['Charging_Power_MW'] == 0) & (df['Discharging_Power_MW'] == 0)
    
    # Identify overlap conditions
    df['Charging_During_Curtailment'] = df['Is_Curtailment'] & df['Is_Battery_Charging']
    df['Discharging_During_Curtailment'] = df['Is_Curtailment'] & df['Is_Battery_Discharging']
    df['Idle_During_Curtailment'] = df['Is_Curtailment'] & df['Is_Battery_Idle']
    

    total_periods = len(df)
    curtailment_periods = df['Is_Curtailment'].sum()
    charging_during_curtailment_periods = df['Charging_During_Curtailment'].sum()
    discharging_during_curtailment_periods = df['Discharging_During_Curtailment'].sum()
    idle_during_curtailment_periods = df['Idle_During_Curtailment'].sum()
    
    total_hours = total_periods * timestep_hours
    curtailment_hours = curtailment_periods * timestep_hours
    charging_during_curtailment_hours = charging_during_curtailment_periods * timestep_hours
    discharging_during_curtailment_hours = discharging_during_curtailment_periods * timestep_hours
    idle_during_curtailment_hours = idle_during_curtailment_periods * timestep_hours
    
    pct_curtailment_periods_charging = (charging_during_curtailment_periods / curtailment_periods * 100) if curtailment_periods > 0 else 0
    pct_curtailment_periods_discharging = (discharging_during_curtailment_periods / curtailment_periods * 100) if curtailment_periods > 0 else 0
    pct_curtailment_periods_idle = (idle_during_curtailment_periods / curtailment_periods * 100) if curtailment_periods > 0 else 0
    
    total_curtailment_energy = df['Curtailment'].sum() * timestep_hours
    curtailment_during_charging = df.loc[df['Charging_During_Curtailment'], 'Curtailment'].sum() * timestep_hours
    curtailment_during_discharging = df.loc[df['Discharging_During_Curtailment'], 'Curtailment'].sum() * timestep_hours
    curtailment_during_idle = df.loc[df['Idle_During_Curtailment'], 'Curtailment'].sum() * timestep_hours
    
    battery_charging_energy_during_curtailment = df.loc[df['Charging_During_Curtailment'], 'Charging_Power_MW'].sum() * timestep_hours
    battery_discharging_energy_during_curtailment = df.loc[df['Discharging_During_Curtailment'], 'Discharging_Power_MW'].sum() * timestep_hours
    
    pct_curtailment_energy_during_charging = (curtailment_during_charging / total_curtailment_energy * 100) if total_curtailment_energy > 0 else 0
    pct_curtailment_energy_during_discharging = (curtailment_during_discharging / total_curtailment_energy * 100) if total_curtailment_energy > 0 else 0
    
    curtailment_capture_efficiency = (battery_charging_energy_during_curtailment / curtailment_during_charging * 100) if curtailment_during_charging > 0 else 0
    additional_excess_energy = battery_discharging_energy_during_curtailment
    
    results = {
        'time_analysis': { 'total_hours': total_hours, 'curtailment_hours': curtailment_hours, 'charging_during_curtailment_hours': charging_during_curtailment_hours, 'discharging_during_curtailment_hours': discharging_during_curtailment_hours, 'idle_during_curtailment_hours': idle_during_curtailment_hours, 'pct_curtailment_periods_charging': pct_curtailment_periods_charging, 'pct_curtailment_periods_discharging': pct_curtailment_periods_discharging, 'pct_curtailment_periods_idle': pct_curtailment_periods_idle },
        'energy_analysis': { 'total_curtailment_energy_mwh': total_curtailment_energy, 'curtailment_during_charging_mwh': curtailment_during_charging, 'curtailment_during_discharging_mwh': curtailment_during_discharging, 'curtailment_during_idle_mwh': curtailment_during_idle, 'pct_curtailment_energy_during_charging': pct_curtailment_energy_during_charging, 'pct_curtailment_energy_during_discharging': pct_curtailment_energy_during_discharging },
        'battery_curtailment_interaction': { 'battery_charging_energy_during_curtailment_mwh': battery_charging_energy_during_curtailment, 'battery_discharging_energy_during_curtailment_mwh': battery_discharging_energy_during_curtailment, 'curtailment_capture_efficiency_pct': curtailment_capture_efficiency, 'additional_excess_energy_from_battery_mwh': additional_excess_energy },
        'summary_metrics': { 'curtailment_periods_total': curtailment_periods, 'curtailment_periods_with_charging': charging_during_curtailment_periods, 'curtailment_periods_with_discharging': discharging_during_curtailment_periods, 'curtailment_capture_ratio': battery_charging_energy_during_curtailment / total_curtailment_energy if total_curtailment_energy > 0 else 0, 'excess_energy_contribution_ratio': additional_excess_energy / total_curtailment_energy if total_curtailment_energy > 0 else 0 }
    }
    
    return results