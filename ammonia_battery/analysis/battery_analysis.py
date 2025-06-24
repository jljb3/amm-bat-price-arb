import os
import pandas as pd
import numpy as np
import json

# Import the specific analysis functions
from .operational_metrics import analyze_time_based_metrics, analyze_operational_efficiency
from .curtailment_analysis import analyze_curtailment_interactions

def analyze_price_response(results_df):
    """
    Extracts price response metrics.
    This function now ONLY performs calculations and returns the results.
    """
    df = results_df.copy()

    price_bins = [-float('inf'), -50, -10, 0, 50, 100, 150, 200, float('inf')]
    price_labels = ['<-50', '-50 to -10', '-10 to 0', '0 to 50', '50 to 100', '100 to 150', '150 to 200', '>200']
    df['price_bin'] = pd.cut(df['Price'], bins=price_bins, labels=price_labels)
    
    price_bin_stats = df.groupby('price_bin').agg(
        hours=('TimeStep', 'count'),
        charging_hours=('Is_Charging', 'sum'),
        discharging_hours=('Is_Discharging', 'sum')
    )
    
    return {'price_bin_stats': price_bin_stats}


def perform_comprehensive_analysis(results_df, max_capacity, output_folder='battery_analysis'):
    """
    Performs comprehensive analysis by orchestrating calls to specific analysis
    functions and handling all file saving.
    """
    os.makedirs(output_folder, exist_ok=True)
    results_df.to_csv(os.path.join(output_folder, 'full_optimization_results.csv'), index=False)
    print(f"Comprehensive analysis started. Results will be saved to '{output_folder}'.")

    print("Analyzing time-based and operational efficiency metrics...")
    time_metrics = analyze_time_based_metrics(results_df)
    efficiency_metrics = analyze_operational_efficiency(results_df, max_capacity)
    
    print("Analyzing price response metrics...")
    price_metrics = analyze_price_response(results_df)
    
    print("Analyzing curtailment correlation metrics...")
    curtailment_metrics = analyze_curtailment_interactions(results_df) 
    
    summary = {
        'economic': {
            'total_profit': results_df['Net_Revenue'].sum(),
            'average_charging_price': results_df.loc[results_df['Charging_Power_MW'] > 0, 'Price'].mean(),
            'average_discharging_price': results_df.loc[results_df['Discharging_Power_MW'] > 0, 'Price'].mean(),
        },
        'operational': {
            'total_charging_hours': time_metrics['monthly_operation']['charging_hours'].sum(),
            'total_discharging_hours': time_metrics['monthly_operation']['discharging_hours'].sum(),
            'total_cycles': time_metrics['transitions']['charging_cycles'],
            'max_storage_utilization': efficiency_metrics['summary']['max_storage_level'] / max_capacity * 100
        }
    }

    print("Saving all analysis results to CSV and JSON...")
    # Save results from time_based analysis
    time_metrics['monthly_operation'].to_csv(os.path.join(output_folder, 'monthly_operation.csv'))
    time_metrics['hourly_by_season'].to_csv(os.path.join(output_folder, 'hourly_operation_by_season.csv'))
    
    # Save results from efficiency analysis
    efficiency_metrics['monthly_utilization'].to_csv(os.path.join(output_folder, 'monthly_capacity_utilization.csv'))
    efficiency_metrics['storage_duration'].to_csv(os.path.join(output_folder, 'storage_duration_distribution.csv'))

    # Save results from price analysis
    price_metrics['price_bin_stats'].to_csv(os.path.join(output_folder, 'price_bin_statistics.csv'))

    # Save summary as JSON
    with open(os.path.join(output_folder, 'analysis_summary.json'), 'w') as f:
        json.dump(summary, f, indent=4, default=str)

    print("Analysis complete!")
    
    # Return a dictionary containing all the calculated metrics for further use
    return {
        'summary': summary,
        'time_metrics': time_metrics,
        'price_metrics': price_metrics,
        'curtailment_metrics': curtailment_metrics,
        'efficiency_metrics': efficiency_metrics
    }