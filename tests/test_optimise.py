import pytest
import pandas as pd
from src.optimise import is_payout_ratio_valid

@pytest.fixture
def sample_history_df():
    """
    Creates a small, mock pandas DataFrame to simulate the last 51 weeks of history.
    The actual values don't matter much for these specific tests, as the logic
    in the `is_payout_ratio_valid` function currently uses the `config` for history.
    However, it's a required argument and good practice to provide it.
    """
    data = {'week_start': pd.to_datetime(['2025-01-01']),
            'tickets_sold': [10000000],
            'net_revenue': [4000000],
            'marketing_spend': [1000000]}
    # In a real test, this would contain 51 rows of representative data.
    return pd.DataFrame(data)

def test_payout_ratio_is_valid(sample_history_df): # <-- Add the fixture as an argument
    """Test that the ratio constraint passes when it should."""
    config = {
        'min_payout_ratio_12m': 0.40,
        'ticket_price': 2.50,
        'secondary_prize_payout_percentage': 0.25,
        'history': {
            'total_prizes_paid_last_51_weeks': 400_000_000,
            'total_sales_revenue_last_51_weeks': 1_000_000_000
        }
    }
    # --- FIX IS HERE: Added 'sample_history_df' as the third argument ---
    assert is_payout_ratio_valid(20_000_000, 10_000_000, sample_history_df, config) is True

def test_payout_ratio_is_invalid(sample_history_df): # <-- Add the fixture as an argument
    """Test that the ratio constraint fails when it should."""
    config = {
        'min_payout_ratio_12m': 0.40,
        'ticket_price': 2.50,
        'secondary_prize_payout_percentage': 0.25,
        'history': {
            'total_prizes_paid_last_51_weeks': 300_000_000, # Lower history
            'total_sales_revenue_last_51_weeks': 1_000_000_000
        }
    }
    # --- FIX IS HERE: Added 'sample_history_df' as the third argument ---
    assert is_payout_ratio_valid(1_000_000, 1_000_000, sample_history_df, config) is False
