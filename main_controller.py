# This script is the main entry point for the Ammonia Battery project.
# It uses the refactored modules to run specific scenarios.
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ammonia_battery.scenarios.manager import run_single_scenario, compare_a2p_scenarios

def main():
    """
    Defines and runs the desired simulation scenarios.
    """
    # --- Define Scenario Parameters ---
    
    DATA_FILE = "/Users/jackburt/Library/CloudStorage/OneDrive-Personal/Documents/Cambridge/PhD/linear_programming/Modelling/integrated_data_2024.csv"
    
    # --- Run a Single, Detailed Scenario ---
    
    run_single_scenario(
        scenario_name="Direct_Combustion_Base_Case",
        data_file=DATA_FILE,
        days_to_run=366,
        p2a_capacity=100,
        a2p_capacity=100,
        a2p_technology="direct_combustion"
    )

    # Run other scenarios to compare them, for example:
    # run_single_scenario(
    #     scenario_name="H2_Combustion_Case",
    #     data_file=DATA_FILE,
    #     days_to_run=366,
    #     p2a_capacity=100,
    #     a2p_capacity=100,
    #     a2p_technology="h2_combustion"
    # )
    
    # --- Run a Quick Comparison Scenario ---
    # This calls the other function from our scenario manager to show a
    # quick, targeted comparison without a full optimization run.
    
    compare_a2p_scenarios(
        p2a_capacity=100,
        storage_capacity=10000
    )


if __name__ == "__main__":
    # This block ensures the main function is called only when the script is executed directly.
    main()