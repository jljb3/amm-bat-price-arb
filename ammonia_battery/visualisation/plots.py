import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import pandas as pd

def plot_results(operational_results):
    """
    Plots the optimization results.

    Uses the actual datetime for the x-axis and sets
    y-axis limits dynamically for greater robustness.

    Parameters:
        operational_results (pd.DataFrame): DataFrame with time series results.

    Returns:
        matplotlib.figure.Figure: The generated plot figure, ready to be saved.
    """
    if operational_results is None or operational_results.empty:
        print("No operational results to plot.")
        return None

    # Ensure the 'Time' column is in datetime format for plotting
    if 'Time' in operational_results.columns and not pd.api.types.is_datetime64_any_dtype(operational_results['Time']):
        operational_results['Time'] = pd.to_datetime(operational_results['Time'])

    # Create figure with GridSpec for better control
    fig = plt.figure(figsize=(15, 10)) # Made slightly wider for datetime labels
    gs = GridSpec(3, 1, height_ratios=[2, 1, 2], hspace=0.4) # Increased hspace for labels

    # --- Panel 1: Charging and Discharging Power ---
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(operational_results['Time'],
             operational_results['Charging_Power_MW'],
             'b-', alpha=0.7, label='Charging Power (MW)')
    ax1.plot(operational_results['Time'],
             operational_results['Discharging_Power_MW'],
             'r-', alpha=0.7, label='Discharging Power (MW)')
    ax1.set_ylabel('Power (MW)')
    ax1.set_title('Power Flow')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    max_power = max(operational_results['Charging_Power_MW'].max(),
                    operational_results['Discharging_Power_MW'].max())
    ax1.set_ylim(0, max_power * 1.1) # Set limit to 110% of max power observed
    ax1.tick_params(axis='x', rotation=45)

    # --- Panel 2: Electricity Price ---
    ax2 = fig.add_subplot(gs[1], sharex=ax1) # Share the x-axis with the plot above
    ax2.plot(operational_results['Time'],
             operational_results['Price'], 'orange', label='Electricity Price (£/MWh)')
    ax2.set_ylabel('Price (£/MWh)')
    ax2.set_title('Electricity Price')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    min_price = operational_results['Price'].min()
    max_price = operational_results['Price'].max()
    ax2.set_ylim(min_price * 1.2, max_price * 1.2) # Add 20% buffer
    ax2.tick_params(axis='x', rotation=45)

    
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax3.plot(operational_results['Time'],
             operational_results['NH3_Level_Tonnes'],
             'g-', label='NH₃ Storage Level (tonnes)')
    ax3.set_ylabel('NH₃ Storage (tonnes)')
    ax3.set_title('NH₃ Storage Level')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    max_storage = operational_results['NH3_Level_Tonnes'].max()
    ax3.set_ylim(0, max_storage * 1.1)
    ax3.tick_params(axis='x', rotation=45)

    # Remove overlapping x-axis labels from the top two plots
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.setp(ax2.get_xticklabels(), visible=False)

    # Add overall title
    fig.suptitle('Ammonia Battery Optimization Results', fontsize=16)

    fig.tight_layout(rect=[0, 0, 1, 0.96]) # Adjust rect to make space for suptitle

    return fig