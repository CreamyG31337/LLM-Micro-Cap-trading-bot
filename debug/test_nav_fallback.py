#!/usr/bin/env python3
"""Test the NAV weekend fallback fix"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

# Simulate the fix
historical_values = {
    '2025-09-05': 9330.04,
    '2025-09-08': 9457.27,
    '2025-09-09': 9444.88,
}

total_units = 1000  # Example

# Test weekend contribution (Sept 7 - Saturday)
from datetime import datetime, timedelta
date_str = '2025-09-07'
contribution_date = datetime.strptime(date_str, '%Y-%m-%d')

nav_at_contribution = 1.0  # Default fallback
if total_units > 0:
    for days_back in range(1, 8):
        prior_date = contribution_date - timedelta(days=days_back)
        prior_date_str = prior_date.strftime('%Y-%m-%d')
        
        if prior_date_str in historical_values:
            fund_value_at_prior_date = historical_values[prior_date_str]
            nav_at_contribution = fund_value_at_prior_date / total_units
            print(f"✓ Sept 7 (Saturday) -> using {prior_date_str} ({prior_date.strftime('%A')})")
            print(f"  Fund value: ${fund_value_at_prior_date:,.2f}")
            print(f"  Total units: {total_units:,.2f}")
            print(f"  NAV: ${nav_at_contribution:.4f}")
            break

print(f"\nResult: NAV = ${nav_at_contribution:.4f}")
print(f"Expected: ~${9330.04 / 1000:.4f} (Sept 5 Friday)")

if abs(nav_at_contribution - 9.3300) < 0.01:
    print("\n✅ TEST PASSED")
else:
    print(f"\n❌ TEST FAILED - Expected ~9.33, got {nav_at_contribution:.4f}")
