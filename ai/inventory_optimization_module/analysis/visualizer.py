import matplotlib.pyplot as plt
import pandas as pd
import os

class Visualizer:
    def __init__(self, output_dir='.'):
        self.output_dir = output_dir

    def plot_inventory_comparison(self, daily_results_dict):
        """
        Plots inventory levels (stock_end) for multiple strategies and highlights stockouts.
        
        Args:
            daily_results_dict (dict): {strategy_name: DataFrame}
                                       DataFrame must have 'date', 'stock_end', 'demand' columns.
        """
        plt.figure(figsize=(12, 6))
        
        # Define some colors for strategies
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        strategy_names = list(daily_results_dict.keys())
        
        # 1. Plot Demand (Background)
        # Assuming demand is the same for all, take from the first one
        if strategy_names:
            first_df = daily_results_dict[strategy_names[0]]
            plt.fill_between(first_df['date'], 0, first_df['demand'], color='gray', alpha=0.2, label='Actual Demand')
        
        # 2. Plot Inventory Levels
        for i, (name, df) in enumerate(daily_results_dict.items()):
            color = colors[i % len(colors)]
            plt.plot(df['date'], df['stock_end'], label=f'{name} (Stock)', color=color, linewidth=2)
            
            # 3. Highlight Stockouts for Rule-Based (or all?) 
            if "Rule-Based" in name:
                stockouts = df[df['stock_end'] == 0]
                if not stockouts.empty:
                    plt.scatter(stockouts['date'], [0] * len(stockouts), color='red', s=50, zorder=5, label='Stockout (Rule-Based)')

        plt.title('Inventory Levels Comparison')
        plt.xlabel('Date')
        plt.ylabel('Units')
        # Handle empty legend if no strategies
        if strategy_names:
            plt.legend(loc='upper right')
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        
        output_path = os.path.join(self.output_dir, 'inventory_comparison.png')
        plt.savefig(output_path)
        plt.close()
        print(f"Saved {output_path}")

    def plot_cost_structure(self, summary_data):
        """
        Plots a stacked bar chart of cost breakdowns.
        
        Args:
            summary_data (list of dict or DataFrame): Must contain 'Strategy', 'Purchase Cost', 
                                                      'Holding Cost', 'Shortage Cost', 'Spoilage Cost'.
        """
        if isinstance(summary_data, list):
            df = pd.DataFrame(summary_data)
        else:
            df = summary_data.copy()
            
        # Ensure we have the right columns
        required_cols = ['Strategy', 'Purchase Cost', 'Holding Cost', 'Shortage Cost', 'Spoilage Cost']
        for col in required_cols:
            if col not in df.columns:
                print(f"Error: Missing column {col} for cost structure plot.")
                return

        strategies = df['Strategy']
        purchase = df['Purchase Cost']
        holding = df['Holding Cost']
        shortage = df['Shortage Cost']
        spoilage = df['Spoilage Cost']
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        bar_width = 0.5
        x = range(len(strategies))
        
        # Stacked Bars
        p1 = ax.bar(x, purchase, width=bar_width, label='Purchase Cost', color='#1f77b4')
        p2 = ax.bar(x, holding, width=bar_width, bottom=purchase, label='Holding Cost', color='#ff7f0e')
        p3 = ax.bar(x, shortage, width=bar_width, bottom=purchase+holding, label='Shortage Cost', color='#d62728')
        p4 = ax.bar(x, spoilage, width=bar_width, bottom=purchase+holding+shortage, label='Spoilage Cost', color='#7f7f7f')
        
        ax.set_title('Cost Structure by Strategy')
        ax.set_xticks(x)
        ax.set_xticklabels(strategies, rotation=15, ha='right')
        ax.set_ylabel('Cost ($)')
        ax.legend()
        
        # Add total labels on top
        totals = purchase + holding + shortage + spoilage
        for i, v in enumerate(totals):
            ax.text(i, v + (v * 0.01), f'${v:,.0f}', ha='center', va='bottom', fontweight='bold')
            
        plt.tight_layout()
        
        output_path = os.path.join(self.output_dir, 'cost_structure.png')
        plt.savefig(output_path)
        plt.close()
        print(f"Saved {output_path}")
