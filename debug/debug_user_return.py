#!/usr/bin/env python3
"""
Debug the user return calculation by bypassing all caching.
Calculates what the correct return should be for lance.colton@gmail.com.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from collections import defaultdict

# Add paths for imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "web_dashboard"))

from dotenv import load_dotenv
load_dotenv()

from web_dashboard.supabase_client import SupabaseClient


def debug_user_return():
    """Calculate user return bypassing all caches."""
    
    fund = "Project Chimera"
    user_email = "lance.colton@gmail.com"
    
    print("="*60)
    print(f"Debugging User Return for {user_email}")
    print(f"Fund: {fund}")
    print("="*60)
    
    client = SupabaseClient(use_service_role=True)
    
    # Step 1: Get current fund value from latest positions (NO CACHE)
    print("\n1. Getting current fund value from latest_positions view...")
    
    positions = client.supabase.table("latest_positions")\
        .select("ticker, shares, current_price, market_value, currency")\
        .eq("fund", fund)\
        .execute()
    
    if not positions.data:
        print("   ERROR: No positions found!")
        return
    
    print(f"   Found {len(positions.data)} positions")
    
    # Get exchange rate
    usd_to_cad = 1.42
    try:
        rate = client.get_latest_exchange_rate('USD', 'CAD')
        if rate:
            usd_to_cad = float(rate)
    except:
        pass
    print(f"   USD/CAD rate: {usd_to_cad}")
    
    # Calculate total value in CAD
    total_value_cad = 0.0
    for pos in positions.data:
        mv = float(pos.get('market_value', 0) or 0)
        currency = pos.get('currency', 'USD')
        if currency == 'USD':
            total_value_cad += mv * usd_to_cad
        else:
            total_value_cad += mv
    
    # Add cash
    cash = client.supabase.table("cash_balances")\
        .select("currency, amount")\
        .eq("fund", fund)\
        .execute()
    
    cash_cad = 0.0
    if cash.data:
        for c in cash.data:
            amt = float(c.get('amount', 0) or 0)
            if c.get('currency') == 'USD':
                cash_cad += amt * usd_to_cad
            else:
                cash_cad += amt
    
    fund_total_value = total_value_cad + cash_cad
    print(f"   Portfolio value: ${total_value_cad:,.2f}")
    print(f"   Cash: ${cash_cad:,.2f}")
    print(f"   TOTAL FUND VALUE: ${fund_total_value:,.2f}")
    
    # Step 2: Get all contributions
    print("\n2. Getting all contributions...")
    
    contributions = client.supabase.table("fund_contributions")\
        .select("contributor, email, amount, contribution_type, timestamp")\
        .eq("fund", fund)\
        .order("timestamp")\
        .execute()
    
    if not contributions.data:
        print("   ERROR: No contributions found!")
        return
    
    print(f"   Found {len(contributions.data)} contribution records")
    
    # Calculate total contributions and user's contribution
    total_contributions = 0.0
    user_net_contribution = 0.0
    
    for c in contributions.data:
        amount = float(c.get('amount', 0))
        ctype = c.get('contribution_type', 'CONTRIBUTION').upper()
        email = (c.get('email') or '').lower()
        
        if ctype == 'WITHDRAWAL':
            total_contributions -= amount
            if email == user_email.lower():
                user_net_contribution -= amount
        else:
            total_contributions += amount
            if email == user_email.lower():
                user_net_contribution += amount
    
    print(f"   Total net contributions: ${total_contributions:,.2f}")
    print(f"   User ({user_email}) net contribution: ${user_net_contribution:,.2f}")
    
    # Step 3: Calculate SIMPLE ownership-based return (no NAV complexity)
    print("\n3. Simple ownership-based calculation:")
    simple_ownership_pct = (user_net_contribution / total_contributions * 100) if total_contributions > 0 else 0
    simple_current_value = fund_total_value * (simple_ownership_pct / 100)
    simple_gain = simple_current_value - user_net_contribution
    simple_gain_pct = (simple_gain / user_net_contribution * 100) if user_net_contribution > 0 else 0
    
    print(f"   Ownership %: {simple_ownership_pct:.2f}%")
    print(f"   Current value: ${simple_current_value:,.2f}")
    print(f"   Gain/Loss: ${simple_gain:,.2f}")
    print(f"   Gain/Loss %: {simple_gain_pct:.2f}%")
    
    # Step 4: Check what NAV calculation would give
    print("\n4. NAV-based calculation (simulating what dashboard does):")
    
    # Get historical positions for NAV calculation
    historical = client.supabase.table("portfolio_positions")\
        .select("date, shares, price, currency")\
        .eq("fund", fund)\
        .order("date")\
        .execute()
    
    # Build historical values by date
    values_by_date = defaultdict(float)
    for row in historical.data or []:
        date_str = row['date'][:10]
        shares = float(row.get('shares', 0))
        price = float(row.get('price', 0))
        currency = row.get('currency', 'USD')
        value = shares * price
        if currency == 'USD':
            value *= usd_to_cad
        values_by_date[date_str] += value
    
    print(f"   Historical dates available: {len(values_by_date)}")
    
    # Sort contributions by timestamp
    sorted_contribs = sorted(contributions.data, key=lambda x: x.get('timestamp') or '')
    
    # Parse contributions
    parsed = []
    for c in sorted_contribs:
        ts = c.get('timestamp')
        if ts:
            try:
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                ts = None
        parsed.append({
            'contributor': c['contributor'],
            'email': (c.get('email') or '').lower(),
            'amount': float(c.get('amount', 0)),
            'type': c.get('contribution_type', 'CONTRIBUTION').upper(),
            'timestamp': ts,
            'date_str': ts.strftime('%Y-%m-%d') if ts else None
        })
    
    # Simulate NAV calculation
    contributor_units = defaultdict(float)
    total_units = 0.0
    
    print("\n   Processing contributions chronologically:")
    for i, contrib in enumerate(parsed[:10]):  # Show first 10
        date_str = contrib['date_str']
        fund_value_at_date = values_by_date.get(date_str) if date_str else None
        
        if total_units == 0:
            nav = 1.0
        elif fund_value_at_date:
            nav = fund_value_at_date / total_units
        else:
            nav = 1.0  # Fallback
        
        if contrib['type'] == 'CONTRIBUTION':
            units = contrib['amount'] / nav
            contributor_units[contrib['contributor']] += units
            total_units += units
        
        if i < 5:
            print(f"     {date_str}: {contrib['contributor'][:15]:<15} ${contrib['amount']:>8,.0f} @ NAV={nav:.4f} = {units:.2f} units (fund_val={fund_value_at_date or 'N/A'})")
    
    if len(parsed) > 10:
        print(f"     ... and {len(parsed) - 10} more contributions")
    
    # Find user's units
    user_contributor = None
    user_units = 0.0
    for contrib in parsed:
        if contrib['email'] == user_email.lower():
            user_contributor = contrib['contributor']
            user_units = contributor_units.get(user_contributor, 0)
            break
    
    print(f"\n   Total units across all contributors: {total_units:.2f}")
    print(f"   User ({user_contributor}) units: {user_units:.2f}")
    
    if total_units > 0:
        current_nav = fund_total_value / total_units
        user_value = user_units * current_nav
        user_ownership = (user_units / total_units) * 100
        user_gain = user_value - user_net_contribution
        user_gain_pct = (user_gain / user_net_contribution * 100) if user_net_contribution > 0 else 0
        
        print(f"   Current NAV: {current_nav:.4f}")
        print(f"   User current value: ${user_value:,.2f}")
        print(f"   User ownership: {user_ownership:.2f}%")
        print(f"   User gain: ${user_gain:,.2f}")
        print(f"   User gain %: {user_gain_pct:.2f}%")
    
    # Step 5: What the dashboard is showing
    print("\n5. What dashboard is showing:")
    print(f"   User Return: $3,854.74 (+63.98%)")
    print(f"   This implies current_value: ${user_net_contribution + 3854.74:,.2f}")
    print(f"   This implies ownership: {(user_net_contribution + 3854.74) / fund_total_value * 100:.1f}%")
    
    print("\n" + "="*60)
    print("DIAGNOSIS:")
    print("="*60)
    if abs(simple_gain_pct - 63.98) > 5:
        print(f"  Simple calculation shows {simple_gain_pct:.1f}% but dashboard shows 63.98%")
        print("  The NAV calculation is producing wrong results.")
        print("  Likely cause: Cached historical fund values from when duplicates existed.")
    else:
        print("  Calculations match - issue may be elsewhere.")


if __name__ == "__main__":
    debug_user_return()
