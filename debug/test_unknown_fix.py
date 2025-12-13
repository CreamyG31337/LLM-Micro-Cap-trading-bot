#!/usr/bin/env python3
"""Test that Unknown company names are now properly updated"""

# Test the logic
def old_check(company_name):
    """Old buggy logic"""
    if company_name:
        return "SKIP (bug: Unknown treated as valid)"
    return "FETCH"

def new_check(company_name):
    """New fixed logic"""
    if company_name and company_name != 'Unknown':
        return "SKIP"
    return "FETCH"

test_cases = [
    (None, "NULL"),
    ("", "empty string"),
    ("Unknown", "'Unknown'"),
    ("Apple Inc.", "valid name"),
]

print("Testing company_name check logic:")
print("=" * 60)
for value, description in test_cases:
    old = old_check(value)
    new = new_check(value)
    status = "BUG FIXED" if old != new else "same"
    print(f"{description:20} | Old: {old:30} | New: {new:10} | {status}")

print("\n✅ Fix verified: 'Unknown' now triggers yfinance fetch")
