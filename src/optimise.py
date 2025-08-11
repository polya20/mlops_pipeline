import argparse, os, pickle, yaml, json
import numpy as np, pandas as pd

def calculate_expected_jackpot_payout(jackpot_millions, predicted_sales, config):
    prob_win = 1 - ((1 - config['prob_single_ticket_win']) ** predicted_sales)
    return (jackpot_millions * 1_000_000) * prob_win

def is_payout_ratio_valid(
    expected_jackpot_payout: float,
    predicted_sales: float,
    historical_df: pd.DataFrame, # Still needed for the real run
    config: dict
) -> bool:
    """
    Checks if a proposed jackpot would violate the 52-week rolling payout ratio.
    """
    ticket_price = config['ticket_price']
    min_payout_ratio = config['min_payout_ratio_12m']

    # --- FIX: Prioritize history from config for testability ---
    # In the real Lambda, you would pre-calculate these from the DataFrame and
    # pass them in the config.
    if 'history' in config:
        hist_prizes = config['history']['total_prizes_paid_last_51_weeks']
        hist_sales_revenue = config['history']['total_sales_revenue_last_51_weeks']
    else:
        # --- This is the logic for the real pipeline run ---
        last_51_weeks = historical_df.sort_values('week_start').tail(51)
        hist_sales_revenue = (last_51_weeks['tickets_sold'] * ticket_price).sum()
        
        # A better estimation of historical prizes
        # Costs = Sales - Net Revenue
        # Prizes = Costs - Marketing
        hist_costs = (last_51_weeks['tickets_sold'] * ticket_price) - (last_51_weeks['net_revenue'] * 1_000_000)
        # Assuming marketing_spend is in the same units as net_revenue (millions)
        hist_marketing_spend = (last_51_weeks['marketing_spend'] * 1_000_000)
        hist_prizes = (hist_costs - hist_marketing_spend).sum()
        # --- End real pipeline logic ---

    # Calculate this week's potential new figures
    new_sales_revenue = predicted_sales * ticket_price
    secondary_prizes = new_sales_revenue * config['secondary_prize_payout_percentage']
    new_prizes_paid = expected_jackpot_payout + secondary_prizes

    # Calculate the new 52-week ratio
    total_52w_sales = hist_sales_revenue + new_sales_revenue
    total_52w_prizes = hist_prizes + new_prizes_paid
    
    if total_52w_sales == 0: return True # Avoid division by zero

    new_ratio = total_52w_prizes / total_52w_sales
    
    return new_ratio >= min_payout_ratio

def find_optimal_jackpot(config, model, data_path, available_cash):
    historical_df = pd.read_csv(data_path)
    country_df = historical_df[historical_df['country'] == config['country_name']].copy()
    country_df['week_start'] = pd.to_datetime(country_df['week_start'])
    jackpot_grid = np.linspace(config['min_jackpot'], config['max_jackpot'], config['optimization_grid_steps'])
    valid_results = []
    for jackpot in jackpot_grid:
        if (jackpot * 1_000_000) > (available_cash - config['safety_buffer']):
            continue
        log_jackpot = np.log([[jackpot]])
        predicted_sales = np.exp(model.predict(log_jackpot))[0]
        expected_payout = calculate_expected_jackpot_payout(jackpot, predicted_sales, config)
        if not is_payout_ratio_valid(expected_payout, predicted_sales, country_df, config):
            continue
        sales_revenue = predicted_sales * config['ticket_price']
        secondary_cost = sales_revenue * config['secondary_prize_payout_percentage']
        net_revenue = sales_revenue - expected_payout - secondary_cost
        valid_results.append({'jackpot': jackpot, 'net_revenue': net_revenue})

    if not valid_results: return {"status": "failed", "reason": "No valid jackpot found"}
    results_df = pd.DataFrame(valid_results)
    optimal_row = results_df.loc[results_df['net_revenue'].idxmax()]
    return optimal_row.to_dict()
