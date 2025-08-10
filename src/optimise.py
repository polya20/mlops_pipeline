import pandas as pd
import numpy as np
import pickle
import yaml
import argparse

def calculate_expected_jackpot_payout(jackpot_millions, predicted_sales, config):
    prob_win = 1 - ((1 - config['prob_single_ticket_win']) ** predicted_sales)
    return (jackpot_millions * 1_000_000) * prob_win

def is_payout_ratio_valid(expected_payout, predicted_sales, config):
    hist_prizes = config['history']['total_prizes_paid_last_51_weeks']
    hist_sales = config['history']['total_sales_revenue_last_51_weeks']
    
    new_sales_revenue = predicted_sales * config['ticket_price']
    secondary_prizes = new_sales_revenue * config['secondary_prize_payout_percentage']
    new_total_prizes = hist_prizes + expected_payout + secondary_prizes
    new_total_sales = hist_sales + new_sales_revenue
    
    if new_total_sales == 0: return True
    return (new_total_prizes / new_total_sales) >= config['min_payout_ratio_12m']

def find_optimal_jackpot(config_path: str):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    with open(config['model_path'], 'rb') as f:
        model = pickle.load(f)

    jackpot_grid = np.linspace(config['min_jackpot'], config['max_jackpot'], config['optimization_grid_steps'])
    
    valid_results = []

    for jackpot in jackpot_grid:
        log_jackpot = np.log([[jackpot]])
        predicted_sales = np.exp(model.predict(log_jackpot))[0]
        
        expected_payout = calculate_expected_jackpot_payout(jackpot, predicted_sales, config)

        if not is_payout_ratio_valid(expected_payout, predicted_sales, config):
            continue
        
        sales_revenue = predicted_sales * config['ticket_price']
        secondary_cost = sales_revenue * config['secondary_prize_payout_percentage']
        net_revenue = sales_revenue - expected_payout - secondary_cost
        
        valid_results.append({'jackpot': jackpot, 'net_revenue': net_revenue})

    if not valid_results:
        print("ERROR: No valid jackpot found.")
        return None

    results_df = pd.DataFrame(valid_results)
    optimal_row = results_df.loc[results_df['net_revenue'].idxmax()]
    
    print(f"--- Optimal Jackpot for {config['country_name']} ---")
    print(f"Recommendation: {optimal_row['jackpot']:.2f} M")
    print(f"Expected Net Revenue: {optimal_row['net_revenue']/1_000_000:.2f} M")
    
    return optimal_row.to_dict()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True, help='Path to config.')
    args = parser.parse_args()
    find_optimal_jackpot(args.config)