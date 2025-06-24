import os
import pyomo.environ as pyo
from pyomo.opt import SolverFactory
import pandas as pd
import numpy as np

from ammonia_battery.process_units.systems import AmmoniaBattery 

from ammonia_battery.economics.metrics import calculate_annualized_cost
from ammonia_battery.economics.metrics import calculate_system_economics_with_optimal_storage

class IntegratedAmmoniaBatteryOptimizer:
    """
    Integrates the physical ammonia battery model with the optimization model
    to maximize profit while tracking ammonia inventory
    """
    def __init__(self,
                 p2a_capacity=100,         # MW
                 storage_capacity=100000,    # tonnes
                 a2p_capacity=100,         # MW
                 a2p_technology="direct_combustion",
                 time_interval_hours=0.5):
        """
        Initialize the optimizer with the physical battery configuration.

        Parameters:
            p2a_capacity: Maximum charging power capacity in MW
            storage_capacity: Maximum ammonia storage capacity in tonnes
            a2p_capacity: Maximum discharging power capacity in MW
            a2p_technology: Technology used for ammonia-to-power conversion
        """
        # Time resolution
        self.time_interval_hours = time_interval_hours

        # Create the physical battery model
        self.battery = AmmoniaBattery(
            name="Optimized_NH3_Battery",
            p2a_capacity=p2a_capacity,
            storage_capacity=storage_capacity,
            a2p_capacity=a2p_capacity,
            a2p_technology=a2p_technology
        )

        # Extract key efficiency parameters from the battery
        self.charging_efficiency = self.battery.p2a.overall_efficiency
        self.discharging_efficiency = self.battery.a2p.power_generation.efficiency

        # For conversion between energy and ammonia
        self.lhv_NH3 = 18.6  # MJ/kg

        # Annualize the CAPEX and calculate annual OPEX
        self.system_costs = self.battery.calculate_total_system_costs()
        self.annualized_capex = calculate_annualized_cost(self.system_costs['total_capex'])
        self.annual_opex = self.system_costs['total_opex']

        # Minimum operation thresholds
        self.min_charging_threshold = 0
        self.min_discharging_threshold = 0

        # Initialize storage for optimization results
        self.optimization_results = None

        # Print system configuration
        self._print_system_info()

    def _print_system_info(self):
        """Print key system information"""
        print("\n=== AMMONIA BATTERY SYSTEM CONFIGURATION ===")
        print(f"P2A Capacity: {self.battery.p2a.max_capacity} MW")
        print(f"Storage Capacity: {self.battery.storage.max_capacity} tonnes")
        print(f"A2P Capacity: {self.battery.a2p.max_capacity} MW")
        print(f"A2P Technology: {self.battery.a2p.conversion_technology}")
        print(f"Charging Efficiency: {self.charging_efficiency:.2%}")
        print(f"Discharging Efficiency: {self.discharging_efficiency:.2%}")
        print(f"Round-Trip Efficiency: {self.charging_efficiency * self.discharging_efficiency:.2%}")
        print(f"Annualized CAPEX: £{self.annualized_capex:,.2f}/year")
        print(f"Annual OPEX: £{self.annual_opex:,.2f}/year")
        print(f"Annual Total Expenditure: £{self.annual_opex + self.annualized_capex:,.2f}/year")
        print("===============================================")

    def create_optimization_model(self):
        """Create the Pyomo optimization model for the ammonia battery with free storage variables"""
        # Create an abstract model
        model = pyo.AbstractModel()

        # Sets
        model.DATETIME = pyo.Set()

        # Time series parameters
        model.PRICE = pyo.Param(model.DATETIME, doc='Energy price at time t (£/MWh)')
        model.DEMAND = pyo.Param(model.DATETIME, doc='Demand at time t (MW)')
        model.WIND = pyo.Param(model.DATETIME, doc='Wind power at time t (MW)')
        model.CURTAILMENT = pyo.Param(model.DATETIME, doc='Curtailed power at time t (MW)')
        model.CARBON_BASED_FUELS = pyo.Param(model.DATETIME, doc='Carbon-based fuel power at time t (MW)')

        # Static parameters from physical model (P2A and A2P capacities remain fixed)
        model.MAXIMUM_CHARGING_POWER = pyo.Param(doc='Maximum charging power capacity (MW)')
        model.MAXIMUM_DISCHARGING_POWER = pyo.Param(doc='Maximum discharging power capacity (MW)')

        model.MIN_CHARGING_THRESHOLD = pyo.Param(doc='Minimum charging power threshold (fraction of maximum)')
        model.MIN_DISCHARGING_THRESHOLD = pyo.Param(doc='Minimum discharging power threshold (fraction of maximum)')

        model.CHARGING_EFFICIENCY = pyo.Param(doc='Charging efficiency (fraction between 0 and 1)')
        model.DISCHARGING_EFFICIENCY = pyo.Param(doc='Discharging efficiency (fraction between 0 and 1)')

        # Temporal parameters
        model.TIMESTEP = pyo.Param(doc='Time between DATEIMEs (hours)')

        # Conversion factor parameters for energy-to-ammonia calculations
        model.LHV_NH3 = pyo.Param(doc='Lower heating value of ammonia (MJ/kg)')
        model.NH3_CONVERSION_FACTOR = pyo.Param(doc='Conversion factor from MWh to tonnes NH3')

        # Decision Variables for Storage Design
        model.OPTIMAL_NH3_CAPACITY = pyo.Var(
            within=pyo.NonNegativeReals,
            bounds=(0, 100000),  # Set a reasonable upper bound to prevent unbounded solutions
            doc='Optimal ammonia storage capacity to be determined by optimization (tonnes)'
        )

        model.OPTIMAL_INITIAL_NH3_LEVEL = pyo.Var(
            within=pyo.NonNegativeReals,
            doc='Optimal initial ammonia level to be determined by optimization (tonnes)'
        )

        # Decision Variables for Operation
        model.CHARGING_POWER = pyo.Var(
            model.DATETIME,
            within=pyo.NonNegativeReals,
            bounds=lambda m, t: (0, m.MAXIMUM_CHARGING_POWER),
            doc='Charging power at time t (MW)'
        )

        model.DISCHARGING_POWER = pyo.Var(
            model.DATETIME,
            within=pyo.NonNegativeReals,
            bounds=lambda m, t: (0, m.MAXIMUM_DISCHARGING_POWER),
            doc='Discharging power at time t (MW)'
        )

        # Ammonia level with dynamic bounds based on optimal capacity
        model.NH3_LEVEL = pyo.Var(
            model.DATETIME,
            within=pyo.NonNegativeReals,
            doc='Ammonia level in storage at time t (tonnes)'
        )

        # Binary Variables for tracking operating states
        model.IS_CHARGING_ON = pyo.Var(model.DATETIME, domain=pyo.Binary,
                            doc='Binary variable indicating if charging is operating at stable levels')
        model.IS_DISCHARGING_ON = pyo.Var(model.DATETIME, domain=pyo.Binary,
                                doc='Binary variable indicating if discharging is operating at stable levels')

        # Add state tracking variables
        model.CHARGING_STARTED = pyo.Var(
            model.DATETIME,
            domain=pyo.Binary,
            doc='Binary variable indicating if charging started at time t'
        )

        model.CHARGING_STOPPED = pyo.Var(
            model.DATETIME,
            domain=pyo.Binary,
            doc='Binary variable indicating if charging stopped at time t'
        )

        # Objective Function - Pure Operational Profit
        def operational_profit_rule(model):
            """
            Maximize pure operational profit without fixed costs.
            Fixed costs will be calculated post-optimization based on optimal storage size.
            """
            return sum(
                (model.PRICE[t] * model.DISCHARGING_POWER[t] * model.TIMESTEP) -  # Revenue from energy sold
                (model.PRICE[t] * model.CHARGING_POWER[t] * model.TIMESTEP)      # Cost of energy purchased
                for t in model.DATETIME
            )

        model.objective = pyo.Objective(rule=operational_profit_rule, sense=pyo.maximize,
                                    doc='Maximize operational profit (fixed costs calculated post-optimization)')

        # CONSTRAINTS

        # Dynamic storage capacity constraint
        def storage_capacity_constraint_rule(model, t):
            """Ensure NH3 level never exceeds the optimal storage capacity"""
            return model.NH3_LEVEL[t] <= model.OPTIMAL_NH3_CAPACITY

        model.storage_capacity_constraint = pyo.Constraint(
            model.DATETIME,
            rule=storage_capacity_constraint_rule,
            doc='Ensure ammonia level does not exceed optimal storage capacity'
        )

        # Initial storage level constraint - link to optimal initial level
        def initial_storage_constraint_rule(model):
            """Ensures the initial storage level does not exceed the optimal capacity."""
            return model.OPTIMAL_INITIAL_NH3_LEVEL <= model.OPTIMAL_NH3_CAPACITY

        model.initial_storage_constraint = pyo.Constraint(
            rule=initial_storage_constraint_rule,
            doc='Ensure optimal initial storage level does not exceed optimal capacity'
        )

        # Ammonia balance constraint using optimal initial level
        def nh3_balance_rule(model, t):
            """
            Track ammonia inventory with optimal initial level as starting point
            """
            if t == list(model.DATETIME)[0]:  # First time step
                return model.NH3_LEVEL[t] == model.OPTIMAL_INITIAL_NH3_LEVEL + \
                    (model.CHARGING_POWER[t] * model.CHARGING_EFFICIENCY * model.TIMESTEP * model.NH3_CONVERSION_FACTOR) - \
                    (model.DISCHARGING_POWER[t] * (1/model.DISCHARGING_EFFICIENCY) * model.TIMESTEP * model.NH3_CONVERSION_FACTOR)
            else:
                prev_t = list(model.DATETIME)[list(model.DATETIME).index(t) - 1]
                return model.NH3_LEVEL[t] == model.NH3_LEVEL[prev_t] + \
                    (model.CHARGING_POWER[t] * model.CHARGING_EFFICIENCY * model.TIMESTEP * model.NH3_CONVERSION_FACTOR) - \
                    (model.DISCHARGING_POWER[t] * (1/model.DISCHARGING_EFFICIENCY) * model.TIMESTEP * model.NH3_CONVERSION_FACTOR)

        model.nh3_balance_constraint = pyo.Constraint(
            model.DATETIME,
            rule=nh3_balance_rule,
            doc='Ammonia balance constraint with optimal initial level'
        )

        # Cyclical constraint - final level must equal initial level
        def cyclical_storage_constraint_rule(model):
            """Ensure final storage level equals initial storage level for cyclical operation"""
            last_t = list(model.DATETIME)[-1]
            return model.NH3_LEVEL[last_t] == model.OPTIMAL_INITIAL_NH3_LEVEL

        model.cyclical_storage_constraint = pyo.Constraint(
            rule=cyclical_storage_constraint_rule,
            doc='Enforce cyclical operation: final storage = initial storage'
        )

        # Minimum charging power constraint
        def min_charging_rule(model, t):
            return model.CHARGING_POWER[t] >= model.MIN_CHARGING_THRESHOLD * model.MAXIMUM_CHARGING_POWER * model.IS_CHARGING_ON[t]

        model.min_charging_constraint = pyo.Constraint(
            model.DATETIME,
            rule=min_charging_rule,
            doc='Enforce minimum charging power when charging is on'
        )

        # Maximum charging power constraint
        def max_charging_rule(model, t):
            return model.CHARGING_POWER[t] <= model.MAXIMUM_CHARGING_POWER * model.IS_CHARGING_ON[t]

        model.max_charging_constraint = pyo.Constraint(
            model.DATETIME,
            rule=max_charging_rule,
            doc='Limit charging power based on binary variable'
        )

        # Minimum discharging power constraint
        def min_discharging_rule(model, t):
            return model.DISCHARGING_POWER[t] >= model.MIN_DISCHARGING_THRESHOLD * model.MAXIMUM_DISCHARGING_POWER * model.IS_DISCHARGING_ON[t]

        model.min_discharging_constraint = pyo.Constraint(
            model.DATETIME,
            rule=min_discharging_rule,
            doc='Enforce minimum discharging power when discharging is on'
        )

        # Maximum discharging power constraint
        def max_discharging_rule(model, t):
            return model.DISCHARGING_POWER[t] <= model.MAXIMUM_DISCHARGING_POWER * model.IS_DISCHARGING_ON[t]

        model.max_discharging_constraint = pyo.Constraint(
            model.DATETIME,
            rule=max_discharging_rule,
            doc='Limit discharging power based on binary variable'
        )

        def no_simultaneous_operation_rule(model, t):
            return model.IS_CHARGING_ON[t] + model.IS_DISCHARGING_ON[t] <= 1

        model.no_simultaneous_charge_discharge = pyo.Constraint(
            model.DATETIME,
            rule=no_simultaneous_operation_rule,
            doc='Prevent simultaneous charging and discharging, but allow idle periods'
        )

        return model

    def prepare_data(self, model, timeseries_df):
        """
        Prepare data for the optimization model with free storage variables.
        Note: initial_nh3 and final_nh3 parameters are no longer needed since these are now decision variables.

        Parameters:
            model: The Pyomo abstract model
            timeseries_df: DataFrame with time series data (must include DATETIME, PRICE, DEMAND columns)

        Returns:
            DataPortal object with loaded data
        """
        # Create data portal
        data = pyo.DataPortal(model=model)

        # Make a copy of the dataframe to avoid modifying the original
        df = timeseries_df.copy()

        # Handle datetime and resampling
        if 'DATETIME' in df.columns:
            df['DATETIME'] = pd.to_datetime(df['DATETIME'])

            original_interval = (df['DATETIME'].iloc[1] - df['DATETIME'].iloc[0]).total_seconds() / 3600

            if self.time_interval_hours != original_interval:
                print(f"Resampling data from {original_interval}-hour to {self.time_interval_hours}-hour intervals...")
                df = df.set_index('DATETIME')
                freq = f"{int(self.time_interval_hours)}H"
                numeric_cols = df.select_dtypes(include=['number']).columns
                df = df[numeric_cols].resample(freq).mean()
                df = df.reset_index()

        # Create the time index for the model
        time_indices = list(range(len(df)))
        data['DATETIME'] = {None: time_indices}

        # Load time series parameters
        data['PRICE'] = dict(zip(time_indices, df['PRICE']))
        data['DEMAND'] = dict(zip(time_indices, df['DEMAND']))
        data['WIND'] = dict(zip(time_indices, df['WIND']))
        data['CURTAILMENT'] = dict(zip(time_indices, df['CURTAILMENT']))
        data['CARBON_BASED_FUELS'] = dict(zip(time_indices, df['CARBON_BASED_FUELS']))

        # Calculate the conversion factor from MWh to tonnes NH3
        nh3_conversion_factor = 3600 / (self.lhv_NH3 * 1000)  # tonnes/MWh

        # Load static parameters
        static_params = {
            'MAXIMUM_CHARGING_POWER': self.battery.p2a.max_capacity,
            'MAXIMUM_DISCHARGING_POWER': self.battery.a2p.max_capacity,
            'CHARGING_EFFICIENCY': self.charging_efficiency,
            'DISCHARGING_EFFICIENCY': self.discharging_efficiency,
            'TIMESTEP': self._get_timestep(df),
            'MIN_CHARGING_THRESHOLD': self.min_charging_threshold,
            'MIN_DISCHARGING_THRESHOLD': self.min_discharging_threshold,
            'LHV_NH3': self.lhv_NH3,  # MJ/kg
            'NH3_CONVERSION_FACTOR': nh3_conversion_factor  # tonnes/MWh
        }

        # Load each static parameter
        for param_name, param_value in static_params.items():
            data[param_name] = {None: param_value}

        return data

    def process_results(self, instance, timeseries_df):
        """
        Extract results from the solved instance with optimal storage design

        Parameters:
            instance: Solved Pyomo instance
            timeseries_df: Original time series dataframe

        Returns:
            Dictionary containing:
                - 'preliminary results'
                
        """
        # Extract optimal design parameters
        optimal_capacity = pyo.value(instance.OPTIMAL_NH3_CAPACITY)
        optimal_initial_level = pyo.value(instance.OPTIMAL_INITIAL_NH3_LEVEL)

        print(f"OPTIMAL STORAGE DESIGN:")
        print(f"Optimal Storage Capacity: {optimal_capacity:,.2f} tonnes")
        print(f"Optimal Initial (/Final Level): {optimal_initial_level:,.2f} tonnes")

        # Extract operational results
        results = []
        timestep = pyo.value(instance.TIMESTEP)
        nh3_conversion_factor = pyo.value(instance.NH3_CONVERSION_FACTOR)

        for t in instance.DATETIME:
            datetime_val = timeseries_df['DATETIME'].iloc[t] if 'DATETIME' in timeseries_df.columns else t

            # Operational variables
            charging_power = pyo.value(instance.CHARGING_POWER[t])
            discharging_power = pyo.value(instance.DISCHARGING_POWER[t])
            nh3_level = pyo.value(instance.NH3_LEVEL[t])

            # Calculate ammonia flows
            charging_efficiency = pyo.value(instance.CHARGING_EFFICIENCY)
            discharging_efficiency = pyo.value(instance.DISCHARGING_EFFICIENCY)

            nh3_produced = charging_power * timestep * charging_efficiency * nh3_conversion_factor
            nh3_consumed = discharging_power * timestep * (1/discharging_efficiency) * nh3_conversion_factor

            # Calculate economics
            price = pyo.value(instance.PRICE[t])
            charging_cost = charging_power * timestep * price
            discharging_revenue = discharging_power * timestep * price

            result_row = {
                'Time': datetime_val,
                'TimeStep': t,
                'Price': price,
                'Charging_Power_MW': charging_power,
                'Discharging_Power_MW': discharging_power,
                'NH3_Level_Tonnes': nh3_level,
                'NH3_Produced_Tonnes': nh3_produced,
                'NH3_Consumed_Tonnes': nh3_consumed,
                'Charging_Cost': charging_cost,
                'Discharging_Revenue': discharging_revenue,
                'Net_Revenue': discharging_revenue - charging_cost,
                'Is_Charging': pyo.value(instance.IS_CHARGING_ON[t]),
                'Is_Discharging': pyo.value(instance.IS_DISCHARGING_ON[t]),
                'Demand': pyo.value(instance.DEMAND[t]),
                'Wind': pyo.value(instance.WIND[t]),
                'Curtailment': pyo.value(instance.CURTAILMENT[t]),
                'Carbon_based_fuels': pyo.value(instance.CARBON_BASED_FUELS[t])
            }

            results.append(result_row)

        results_df = pd.DataFrame(results)

        # Calculate cumulative values
        results_df['Cumulative_NH3_Produced'] = results_df['NH3_Produced_Tonnes'].cumsum()
        results_df['Cumulative_NH3_Consumed'] = results_df['NH3_Consumed_Tonnes'].cumsum()
        results_df['Cumulative_Net_Revenue'] = results_df['Net_Revenue'].cumsum()

        # Calculate total operational profit
        total_operational_profit = results_df['Net_Revenue'].sum()

        objective_value = pyo.value(instance.objective)

        print(f"Total Operational Profit: £{total_operational_profit:,.2f}")
        print(f"Objective Function Value: £{objective_value:,.2f}")

        preliminary_results = {
            'operational_results': results_df,
            'optimal_design': {
                'optimal_capacity_tonnes': pyo.value(instance.OPTIMAL_NH3_CAPACITY),
                'optimal_initial_level_tonnes': pyo.value(instance.OPTIMAL_INITIAL_NH3_LEVEL),
            },
            'economics': {
                 'period_operational_profit': total_operational_profit,
                 'period_hours': len(results_df) * pyo.value(instance.TIMESTEP)
            }
        }

        # Calculate total system economics with optimal storage
        final_economics = calculate_system_economics_with_optimal_storage(
            results_dict=preliminary_results,
            system_costs=self.system_costs 
        )

        # Package results
        preliminary_results['economics'] = final_economics
        
        return preliminary_results

    def optimize(self, timeseries_df, mipgap=0.01):
        """
        Run the optimization with free storage variables.

        Parameters:
            timeseries_df: DataFrame with time series data
            mipgap: MIP gap tolerance (default: 0.01 or 1%)

        Returns:
            Dictionary with optimization results including optimal design
        """
        print("Creating optimization model with free storage variables...")
        model = self.create_optimization_model()

        print("Preparing data...")
        data = self.prepare_data(model, timeseries_df)  # No longer need initial/final NH3 parameters

        print("Creating model instance...")
        instance = model.create_instance(data)

        print(f"Solving optimization problem using GLPK (mipgap={mipgap})...")
        solver = SolverFactory('glpk')
        results = solver.solve(instance, tee=True, options={'mipgap': mipgap})

        if (results.solver.status == 'ok' and
            (results.solver.termination_condition == 'optimal' or
            results.solver.termination_condition == 'feasible')):
            print("Optimization completed successfully with optimal or feasible solution.")
        else:
            print(f"Optimization failed: {results.solver.status}, {results.solver.termination_condition}")
            return None

        print("Processing results...")
        self.optimization_results = self.process_results(instance, timeseries_df)

        return self.optimization_results

    def _get_timestep(self, df):
        """Return the configured time interval in hours"""
        return self.time_interval_hours