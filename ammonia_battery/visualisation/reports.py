# ammonia_battery/visualization/reports.py

import os

def format_curtailment_analysis_for_summary(curtailment_results):
    """
    Formats curtailment analysis results into a string suitable for a summary file.
    This function has been moved here from the original curtailment_analysis.py.
    
    Parameters:
        curtailment_results: Dictionary returned by analyze_curtailment_interactions()
    
    Returns:
        Formatted string for inclusion in a summary file.
    """
    
    time_analysis = curtailment_results['time_analysis']
    energy_analysis = curtailment_results['energy_analysis']
    battery_interaction = curtailment_results['battery_curtailment_interaction']
    summary_metrics = curtailment_results['summary_metrics']
    
    # Handle potential division by zero if total_hours is 0
    curtailment_pct = (time_analysis['curtailment_hours'] / time_analysis['total_hours'] * 100) if time_analysis['total_hours'] > 0 else 0

    # Using an f-string for clarity
    summary_text = f"""
CURTAILMENT INTERACTION ANALYSIS
--------------------------------------------------

TIME-BASED ANALYSIS:
  Total simulation period:           {time_analysis['total_hours']:,.0f} hours
  Hours with curtailment:            {time_analysis['curtailment_hours']:,.0f} hours ({curtailment_pct:.1f}% of total time)
  
  Battery behavior during curtailment periods:
  - Charging:                        {time_analysis['charging_during_curtailment_hours']:,.0f} hours ({time_analysis['pct_curtailment_periods_charging']:.1f}% of curtailment periods)
  - Discharging:                     {time_analysis['discharging_during_curtailment_hours']:,.0f} hours ({time_analysis['pct_curtailment_periods_discharging']:.1f}% of curtailment periods)
  - Idle:                            {time_analysis['idle_during_curtailment_hours']:,.0f} hours ({time_analysis['pct_curtailment_periods_idle']:.1f}% of curtailment periods)

ENERGY-BASED ANALYSIS:
  Total curtailed energy:            {energy_analysis['total_curtailment_energy_mwh']:,.0f} MWh
  
  Curtailment energy breakdown by battery state:
  - During battery charging:         {energy_analysis['curtailment_during_charging_mwh']:,.0f} MWh ({energy_analysis['pct_curtailment_energy_during_charging']:.1f}% of total curtailment)
  - During battery discharging:      {energy_analysis['curtailment_during_discharging_mwh']:,.0f} MWh ({energy_analysis['pct_curtailment_energy_during_discharging']:.1f}% of total curtailment)
  - During battery idle:             {energy_analysis['curtailment_during_idle_mwh']:,.0f} MWh

CURTAILMENT CAPTURE ANALYSIS:
  Battery charging during curtailment: {battery_interaction['battery_charging_energy_during_curtailment_mwh']:,.0f} MWh
  Curtailment capture efficiency:    {battery_interaction['curtailment_capture_efficiency_pct']:.1f}%
  Overall curtailment capture ratio: {summary_metrics['curtailment_capture_ratio']*100:.1f}%
  
  Battery discharging during curtailment: {battery_interaction['battery_discharging_energy_during_curtailment_mwh']:,.0f} MWh
  Additional excess energy created:  {summary_metrics['excess_energy_contribution_ratio']*100:.1f}% of total curtailment
"""
    
    # Add interpretation based on the results
    capture_ratio = summary_metrics['curtailment_capture_ratio'] * 100
    excess_ratio = summary_metrics['excess_energy_contribution_ratio'] * 100
    
    interpretation_text = "\nINTERPRETATION:\n"
    if capture_ratio > 10:
        interpretation_text += "HIGH CURTAILMENT CAPTURE: The battery effectively captures significant curtailed energy.\n"
    elif capture_ratio > 5:
        interpretation_text += "MODERATE CURTAILMENT CAPTURE: The battery captures some curtailed energy.\n"
    else:
        interpretation_text += "LOW CURTAILMENT CAPTURE: The battery captures minimal curtailed energy.\n"
    
    if excess_ratio > 5:
        interpretation_text += "SIGNIFICANT EXCESS ENERGY GENERATION: The battery discharges frequently during curtailment periods.\n"
    elif excess_ratio > 1:
        interpretation_text += "MODERATE EXCESS ENERGY GENERATION: Some battery discharging occurs during curtailment.\n"
    else:
        interpretation_text += "MINIMAL EXCESS ENERGY GENERATION: The battery rarely discharges during curtailment.\n"
    
    return summary_text + interpretation_text

def generate_summary_report(output_folder, results_dict, optimizer_params, operational_metrics, curtailment_results, lcoa_results, lcoe_results, lcos_results):
    """
    Generates a detailed text summary file from the optimization and analysis results.
    """
    os.makedirs(output_folder, exist_ok=True)
    filepath = os.path.join(output_folder, 'summary.txt')

    optimal_design = results_dict['optimal_design']
    economics = results_dict['economics']

    with open(filepath, 'w') as f:
        f.write("AMMONIA BATTERY OPTIMIZATION SUMMARY\n")
        f.write("=" * 70 + "\n\n")

        f.write("OPTIMAL SYSTEM DESIGN\n")
        f.write(f"  Optimal Storage Capacity: {optimal_design['optimal_capacity_tonnes']:,.0f} tonnes\n")
        f.write(f"  Initial Storage Level:    {optimal_design['optimal_initial_level_tonnes']:,.0f} tonnes\n")
        f.write(f"  P2A Capacity:             {optimizer_params['p2a_capacity']} MW (fixed)\n")
        f.write(f"  A2P Capacity:             {optimizer_params['a2p_capacity']} MW (fixed)\n")
        f.write(f"  A2P Technology:           {optimizer_params['a2p_technology']}\n\n")

        f.write("EFFICIENCY PARAMETERS\n")
        f.write(f"  Charging Efficiency:      {optimizer_params['charging_efficiency']:.2%}\n")
        f.write(f"  Discharging Efficiency:   {optimizer_params['discharging_efficiency']:.2%}\n")
        f.write(f"  Round-Trip Efficiency:    {optimizer_params['charging_efficiency'] * optimizer_params['discharging_efficiency']:.2%}\n\n")

        f.write("OPERATIONAL PERFORMANCE\n")
        f.write(f"  Annual Charging Hours:         {operational_metrics['annual_charging_hours']:,.0f} hours/year\n")
        f.write(f"  Annual Discharging Hours:      {operational_metrics['annual_discharging_hours']:,.0f} hours/year\n")
        f.write(f"  Charging CAPEX Utilization:    {operational_metrics['charging_capex_utilization']:.1%}\n")
        f.write(f"  Discharging CAPEX Utilization: {operational_metrics['discharging_capex_utilization']:.1%}\n")
        f.write(f"  Electrolyser Replacements:     {operational_metrics['num_electrolyser_replacements']} (over 25 years)\n\n")

        f.write("ECONOMIC ANALYSIS\n")
        f.write(f"  Annual Operational Profit: £{economics['annual_operational_profit']:,.0f}\n")
        f.write(f"  Total System CAPEX:        £{economics['total_system_capex']:,.0f}\n")
        f.write(f"  Annualized CAPEX:          £{economics['annualized_capex']:,.0f}\n")
        f.write(f"  Total Annual OPEX:         £{economics['total_annual_opex']:,.0f}\n")
        f.write(f"  Net Annual Profit:         £{economics['net_annual_profit']:,.0f}\n\n")

        f.write("LEVELIZED COST ANALYSIS\n")
        if lcoa_results:
            f.write(f"  LCOA: £{lcoa_results['lcoa_per_tonne']:,.0f}/tonne NH₃\n")
        if lcoe_results:
            f.write(f"  LCOE: £{lcoe_results['lcoe_per_mwh']:,.0f}/MWh\n")
        if lcos_results:
            f.write(f"  LCOS: £{lcos_results['lcos_per_mwh']:,.0f}/MWh\n")

        # Call the local formatting function to get the curtailment summary text
        if curtailment_results:
            curtailment_text = format_curtailment_analysis_for_summary(curtailment_results)
            f.write(curtailment_text)

        f.write("\n" + "=" * 70 + "\n")

    print(f"Summary report saved to {filepath}")