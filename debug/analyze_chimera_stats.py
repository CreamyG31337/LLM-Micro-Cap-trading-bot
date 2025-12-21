#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script to analyze inflated stats for Project Chimera.
Compares data between Project Chimera and RRSP Lance Webull to find the issue.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from collections import defaultdict

# Force UTF-8 output
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add paths for imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "web_dashboard"))

from dotenv import load_dotenv
load_dotenv()

from web_dashboard.supabase_client import SupabaseClient


def analyze_fund(client, fund_name: str):
    """Analyze a fund's data for issues."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {fund_name}")
    print(f"{'='*60}")
    
    # Get latest date's positions
    today = datetime.now().date()
    start_of_day = datetime.combine(today, datetime.min.time()).isoformat()
    end_of_day = datetime.combine(today, datetime.max.time()).isoformat()
    
    result = client.supabase.table("portfolio_positions")\
        .select("*")\
        .eq("fund", fund_name)\
        .gte("date", start_of_day)\
        .lt("date", end_of_day)\
        .execute()
    
    if not result.data:
        print(f"  No data for today, checking yesterday...")
        yesterday = today - timedelta(days=1)
        start_of_day = datetime.combine(yesterday, datetime.min.time()).isoformat()
        end_of_day = datetime.combine(yesterday, datetime.max.time()).isoformat()
        
        result = client.supabase.table("portfolio_positions")\
            .select("*")\
            .eq("fund", fund_name)\
            .gte("date", start_of_day)\
            .lt("date", end_of_day)\
            .execute()
    
    if not result.data:
        print("  No recent data found!")
        return
    
    # Check for duplicates
    positions = result.data
    date_found = positions[0]['date'][:10]
    print(f"\n  Date: {date_found}")
    print(f"  Total position rows: {len(positions)}")
    
    # Check for duplicate tickers
    ticker_counts = defaultdict(int)
    for pos in positions:
        ticker_counts[pos['ticker']] += 1
    
    duplicates = {t: c for t, c in ticker_counts.items() if c > 1}
    if duplicates:
        print(f"\n  *** DUPLICATES FOUND:")
        for ticker, count in duplicates.items():
            print(f"     {ticker}: {count} entries")
    else:
        print(f"\n  [OK] No duplicate tickers")
    
    # Calculate totals
    total_value = Decimal('0')
    total_cost_basis = Decimal('0')
    total_pnl = Decimal('0')
    
    print(f"\n  Position Details:")
    print(f"  {'Ticker':<10} {'Shares':<12} {'Price':<10} {'Cost Basis':<12} {'PnL':<12} {'Total Val':<12}")
    print(f"  {'-'*70}")
    
    for pos in positions:
        shares = Decimal(str(pos.get('shares', 0)))
        price = Decimal(str(pos.get('price', 0)))
        cost_basis = Decimal(str(pos.get('cost_basis', 0)))
        pnl = Decimal(str(pos.get('pnl', 0)))
        tv = shares * price  # This is how total_value is computed
        
        total_value += tv
        total_cost_basis += cost_basis
        total_pnl += pnl
        
        print(f"  {pos['ticker']:<10} {float(shares):<12.4f} ${float(price):<9.2f} ${float(cost_basis):<11.2f} ${float(pnl):<11.2f} ${float(tv):<11.2f}")
    
    print(f"\n  Summary:")
    print(f"    Total Value (computed): ${float(total_value):,.2f}")
    print(f"    Total Cost Basis:       ${float(total_cost_basis):,.2f}")
    print(f"    Total PnL:              ${float(total_pnl):,.2f}")
    
    # Calculate performance
    if total_cost_basis > 0:
        performance_pct = (total_pnl / total_cost_basis) * 100
        print(f"\n    Performance (pnl/cost_basis): {float(performance_pct):.2f}%")
    
    # Verify PnL = total_value - cost_basis
    computed_pnl = total_value - total_cost_basis
    print(f"\n    Computed PnL (value - cost_basis): ${float(computed_pnl):,.2f}")
    
    pnl_difference = abs(total_pnl - computed_pnl)
    if pnl_difference > 1:  # Allow $1 rounding difference
        print(f"    *** PnL MISMATCH: stored ${float(total_pnl):,.2f} vs computed ${float(computed_pnl):,.2f}")
        print(f"       Difference: ${float(pnl_difference):,.2f}")
    else:
        print(f"    [OK] PnL matches (value - cost_basis)")
    
    # Check historical performance trend
    print(f"\n  Historical Performance Check (last 5 days):")
    for i in range(5):
        check_date = today - timedelta(days=i)
        start_d = datetime.combine(check_date, datetime.min.time()).isoformat()
        end_d = datetime.combine(check_date, datetime.max.time()).isoformat()
        
        hist_result = client.supabase.table("portfolio_positions")\
            .select("total_value, cost_basis, pnl")\
            .eq("fund", fund_name)\
            .gte("date", start_d)\
            .lt("date", end_d)\
            .execute()
        
        if hist_result.data:
            tv_sum = sum(Decimal(str(p.get('total_value', 0) or 0)) for p in hist_result.data)
            cb_sum = sum(Decimal(str(p.get('cost_basis', 0) or 0)) for p in hist_result.data)
            pnl_sum = sum(Decimal(str(p.get('pnl', 0) or 0)) for p in hist_result.data)
            
            if cb_sum > 0:
                perf = (pnl_sum / cb_sum) * 100
                print(f"    {check_date}: TV=${float(tv_sum):,.0f} CB=${float(cb_sum):,.0f} PnL=${float(pnl_sum):,.0f} Perf={float(perf):.2f}%")
            else:
                print(f"    {check_date}: No cost basis")
        else:
            print(f"    {check_date}: No data")
    
    return {
        'total_value': float(total_value),
        'cost_basis': float(total_cost_basis),
        'pnl': float(total_pnl)
    }


def check_contribution_data(client, fund_name: str, user_email: str = "lance.colton@gmail.com"):
    """Check contribution data for NAV calculations."""
    print(f"\n  Contribution Data for {user_email}:")
    
    result = client.supabase.table("fund_contributions")\
        .select("*")\
        .eq("fund", fund_name)\
        .execute()
    
    if not result.data:
        print("    No contributions found")
        return
    
    # Group by contributor
    by_contributor = defaultdict(list)
    for c in result.data:
        by_contributor[c['contributor']].append(c)
    
    print(f"    Total contributors: {len(by_contributor)}")
    
    for contributor, contribs in by_contributor.items():
        net = sum(
            float(c['amount']) if c.get('contribution_type', 'CONTRIBUTION').upper() == 'CONTRIBUTION' 
            else -float(c['amount'])
            for c in contribs
        )
        email = contribs[0].get('email', '')
        print(f"    {contributor}: Net ${net:,.2f} (email: {email})")


def main():
    print("="*60)
    print("Project Chimera Stats Analysis")
    print("="*60)
    
    client = SupabaseClient(use_service_role=True)
    
    # Analyze both funds
    chimera_data = analyze_fund(client, "Project Chimera")
    webull_data = analyze_fund(client, "RRSP Lance Webull")
    
    # Check contribution data
    check_contribution_data(client, "Project Chimera")
    check_contribution_data(client, "RRSP Lance Webull")
    
    print("\n" + "="*60)
    print("Summary Comparison")
    print("="*60)
    
    if chimera_data and webull_data:
        print(f"\nProject Chimera:")
        print(f"  Total Value: ${chimera_data['total_value']:,.2f}")
        print(f"  Cost Basis:  ${chimera_data['cost_basis']:,.2f}")
        print(f"  PnL:         ${chimera_data['pnl']:,.2f}")
        if chimera_data['cost_basis'] > 0:
            print(f"  Performance: {(chimera_data['pnl'] / chimera_data['cost_basis']) * 100:.2f}%")
        
        print(f"\nRRSP Lance Webull:")
        print(f"  Total Value: ${webull_data['total_value']:,.2f}")
        print(f"  Cost Basis:  ${webull_data['cost_basis']:,.2f}")
        print(f"  PnL:         ${webull_data['pnl']:,.2f}")
        if webull_data['cost_basis'] > 0:
            print(f"  Performance: {(webull_data['pnl'] / webull_data['cost_basis']) * 100:.2f}%")


if __name__ == "__main__":
    main()
