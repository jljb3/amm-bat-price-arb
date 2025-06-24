# ammonia_battery/scenarios/manager.py

import pandas as pd
import os

# Import the necessary components from our refactored modules
from ammonia_battery.optimisation.engine import IntegratedAmmoniaBatteryOptimizer
from ammonia_battery.process_units.systems import AmmoniaBattery
from ammonia_battery.visualisation.plots import plot_results
from ammonia_battery.visualisation.reports import generate_summary_report
from ammonia_battery.economics.metrics import (
    calculate_lcos,
    calculate_lcoa,
    calculate_lcoe,
)
from ammonia_battery.analysis.curtailment_analysis import analyze_curtailment_interactions
from ammonia_battery.analysis.operational_metrics import calculate_summary_operational_metrics


def run_single_scenario(
    scenario_name,
    data_file,
    days_to_run=366,
    p2a_capacity=100,
    a2p_capacity=100,
    a2p_technology="direct_combustion"
):
    """
    Runs a complete optimization and analysis for a single, defined scenario.
    """
    print(f"\n===== RUNNING SCENARIO: {scenario_name} =====")
    output_folder = f"results/{scenario_name}"
    os.makedirs(output_folder, exist_ok=True)

    # 1. Load and prepare data
    timeseries_df = pd.read_csv(data_file)
    timeseries_df['DATETIME'] = pd.to_datetime(timeseries_df['DATETIME'])
    periods_per_day = 48
    test_period = days_to_run * periods_per_day
    test_df = timeseries_df.iloc[:test_period].copy()

    # 2. Initialize and run the optimizer
    optimizer = IntegratedAmmoniaBatteryOptimizer(
        p2a_capacity=p2a_capacity,
        a2p_capacity=a2p_capacity,
        a2p_technology=a2p_technology,
        time_interval_hours=0.5
    )
    results_dict = optimizer.optimize(test_df)

    if not results_dict:
        print(f"Scenario '{scenario_name}' failed to optimize. Skipping further analysis.")
        return None

    # 3. Post-processing and analysis
    operational_results = results_dict['operational_results']

    # REFINEMENT: Replace the simplified dict with a call to our new, accurate function
    op_metrics_summary = calculate_summary_operational_metrics(
        results_df=operational_results,
        p2a_capacity_mw=p2a_capacity,
        a2p_capacity_mw=a2p_capacity
    )

    curtailment_results = analyze_curtailment_interactions(operational_results)
    
    # REFINEMENT: Use the correct, full function names in the calls
    lcoa_results = calculate_lcoa(
        results_dict=results_dict,
        a2p_technology=a2p_technology,
        electrolyser_total_capex=optimizer.battery.p2a.electrolyser.sized_capex,
        annual_p2a_opex=optimizer.battery.p2a.calculate_annual_opex()
    )

    lcoe_results = calculate_lcoe(
        results_dict=results_dict,
        lcoa_results=lcoa_results,
        annual_a2p_opex=optimizer.battery.a2p.calculate_annual_opex()
    )

    lcos_results = calculate_lcos(
        results_dict=results_dict,
        a2p_technology=a2p_technology,
        electrolyser_total_capex=optimizer.battery.p2a.electrolyser.sized_capex
    )

    optimizer_params = {
        'p2a_capacity': p2a_capacity,
        'a2p_capacity': a2p_capacity,
        'a2p_technology': a2p_technology,
        'charging_efficiency': optimizer.charging_efficiency,
        'discharging_efficiency': optimizer.discharging_efficiency
    }

    # 4. Generate outputs
    operational_results.to_csv(os.path.join(output_folder, 'optimization_results.csv'), index=False)
    
    fig = plot_results(operational_results)
    if fig:
        fig.savefig(os.path.join(output_folder, 'optimization_plot.png'))

    generate_summary_report(
        output_folder=output_folder,
        results_dict=results_dict,
        optimizer_params=optimizer_params,
        operational_metrics=op_metrics_summary, # Now using the full, accurate metrics
        curtailment_results=curtailment_results,
        lcoa_results=lcoa_results,
        lcoe_results=lcoe_results,
        lcos_results=lcos_results
    )

    print(f"===== SCENARIO '{scenario_name}' COMPLETE =====")
    return results_dict


def compare_a2p_scenarios(p2a_capacity, storage_capacity):
    """
    Compares different ammonia-to-power technologies.
    """
    print("\n--- Comparing A2P Technology Scenarios ---")
    technologies = ["direct_combustion", "blend_combustion", "h2_combustion"]
    tech_names = ["Direct NH₃ Combustion", "Blend Combustion", "H₂ Combustion"]

    print(f"{'Technology':<25} {'Efficiency':<15} {'A2P CAPEX (£M)':<20}")
    print("-" * 60)

    for tech, name in zip(technologies, tech_names):
        battery = AmmoniaBattery(
            name=f"Comparison_{tech}",
            p2a_capacity=p2a_capacity,
            storage_capacity=storage_capacity,
            a2p_capacity=100,
            a2p_technology=tech
        )
        system_costs = battery.calculate_total_system_costs()
        a2p_efficiency = battery.a2p.power_generation.efficiency
        print(f"{name:<25} {a2p_efficiency:<15.2%} £{system_costs['a2p_capex']/1e6:<20,.2f}")
    print("--- End of Comparison ---")