#!/usr/bin/env python3
"""
Test the smart filtering logic for Congress trades
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from scripts.analyze_congress_trades_batch import is_low_risk_asset

# Test cases
test_cases = [
    {
        'name': 'ETF by ticker (SPY)',
        'context': {
            'type': 'Purchase',
            'ticker': 'SPY',
            'company_name': 'SPDR S&P 500 ETF Trust',
            'sector': 'Index Fund'
        },
        'expected': True
    },
    {
        'name': 'ETF by company name',
        'context': {
            'type': 'Sale',
            'ticker': 'VEE.TO',
            'company_name': 'Emerging markets ETF with exposure to China',
            'sector': 'Unknown'
        },
        'expected': True
    },
    {
        'name': 'Mutual Fund',
        'context': {
            'type': 'Purchase',
            'ticker': 'VFINX',
            'company_name': 'Vanguard 500 Index Fund',
            'sector': 'Financial Services'
        },
        'expected': True
    },
    {
        'name': 'Bond/Treasury',
        'context': {
            'type': 'Purchase',
            'ticker': 'TLT',
            'company_name': 'iShares 20+ Year Treasury Bond ETF',
            'sector': 'Bond'
        },
        'expected': True
    },
    {
        'name': 'Non-Purchase/Sale transaction',
        'context': {
            'type': 'Exchange',
            'ticker': 'AAPL',
            'company_name': 'Apple Inc',
            'sector': 'Technology'
        },
        'expected': True
    },
    {
        'name': 'Regular stock (should not filter)',
        'context': {
            'type': 'Purchase',
            'ticker': 'AAPL',
            'company_name': 'Apple Inc',
            'sector': 'Technology'
        },
        'expected': False
    },
    {
        'name': 'Defense contractor (should not filter)',
        'context': {
            'type': 'Sale',
            'ticker': 'RTX',
            'company_name': 'RTX Corporation',
            'sector': 'Aerospace & Defense'
        },
        'expected': False
    }
]

print("Testing Smart Filtering Logic")
print("=" * 80)

passed = 0
failed = 0

for test in test_cases:
    is_filtered, reason = is_low_risk_asset(test['context'])
    expected = test['expected']
    status = "✅ PASS" if is_filtered == expected else "❌ FAIL"
    
    if is_filtered == expected:
        passed += 1
    else:
        failed += 1
    
    print(f"\n{status} - {test['name']}")
    print(f"  Expected: {'Filtered' if expected else 'Not Filtered'}")
    print(f"  Actual: {'Filtered' if is_filtered else 'Not Filtered'}")
    if is_filtered:
        print(f"  Reason: {reason}")

print("\n" + "=" * 80)
print(f"Results: {passed} passed, {failed} failed")

sys.exit(0 if failed == 0 else 1)
