import pytest
from src.optimise import is_payout_ratio_valid

def test_payout_ratio_is_valid():
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
    # Expected new ratio will be > 0.40, so this should pass
    assert is_payout_ratio_valid(20_000_000, 10_000_000, config) is True

def test_payout_ratio_is_invalid():
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
    # Expected new ratio will be < 0.40, so this should fail
    assert is_payout_ratio_valid(1_000_000, 1_000_000, config) is False