main_controller.py: This is the main script to run the optimisation and data processing
process_units/equipment.py: Defines all the process unit equipment
process_units/systems.py: Compiles the process unit equipment into different systems (the charging, discharging and overall ammonia battery)
optimsation/engine.py: The optimisation file itself. Contains the decision variables, sets, constraints, objective function
economics/metrics.py: Defines all of the key economic metrics inclduing the levelized cost of ammonia, levelised cost of the electricity, levelised cost of storage. Also calculates the cost of the system
analysis/battery_analysis.py: Conducts a complete analysis of the battery performances including temporal, price, curtailment and efficiency metrics
analysis/curtailment_analysis.py: Analyses curtailemnt patterns within the data and how the battery operation lines up wiht the presences of curtailment
analysis/operational_metrics.py: Temporal and utilization metrics
visualisation/reports.py: Complies all of the analysis into trext for human interpetation
visualisation/plots.py: Creates a panel plot of the charging/dicharging decision made by the battery, electricty price and the storage level in the stoareg tank
scenarios/manager.py: Loads and prepares teh data, runs the optimisation, process the resulst and outputs a summary of the operation
Integrated_data_2024.csv: The data that goes into the model