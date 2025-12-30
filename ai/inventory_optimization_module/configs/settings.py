# Inventory Simulation Constants

# Financials
PRICE = 50.0
COST = 30.0
HOLDING_COST = 1.0  # Per unit per day
SHORTAGE_COST = 20.0  # Per unit (Lost sale penalty + Opportunity cost)
# Note: Opportunity cost (Margin) is (PRICE - COST) = 20.
# If SHORTAGE_COST is explicitly 20 ON TOP of margin, total underage cost is 40.
# If SHORTAGE_COST represents the total impact of a stockout, it might just be the margin.
# We will interpret SHORTAGE_COST as the *penalty* parameter for the simulation logic.

# Operations
LEAD_TIME = 1  # Days
SHELF_LIFE = 3 # Days (Assumed for "Fresh Retail")

# Simulation
RANDOM_SEED = 42
