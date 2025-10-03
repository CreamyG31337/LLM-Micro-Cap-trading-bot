#!/usr/bin/env python3
"""
Calculate performance data from trade log to show actual daily performance
"""

import os
import pandas as pd
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def calculate_performance_from_trades():
    """Calculate performance data from trade log"""
    print("Calculating performance from trade log...")
    
    # Get trade log data
    url = "https://injqbxdqyxfvannygadt.supabase.co/rest/v1/trade_log"
    headers = {
        "apikey": "SUPABASE_PUBLISHABLE_KEY_REDACTED",
        "Authorization": "Bearer SUPABASE_PUBLISHABLE_KEY_REDACTED",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            trades = response.json()
            print(f"Found {len(trades)} trade records")
            
            # Convert to DataFrame
            df = pd.DataFrame(trades)
            df['date'] = pd.to_datetime(df['date'])
            
            # Calculate cumulative performance by date
            daily_data = []
            cumulative_cost = 0
            cumulative_pnl = 0
            
            for date, group in df.groupby(df['date'].dt.date):
                # Calculate daily trades
                daily_cost = group['cost_basis'].sum()
                daily_pnl = group['pnl'].sum()
                
                # Update cumulative values
                cumulative_cost += daily_cost
                cumulative_pnl += daily_pnl
                
                # Calculate total value
                total_value = cumulative_cost + cumulative_pnl
                performance_pct = (cumulative_pnl / cumulative_cost * 100) if cumulative_cost > 0 else 0
                
                daily_data.append({
                    "fund": "Project Chimera",
                    "date": date.strftime("%Y-%m-%d"),
                    "total_value": round(total_value, 2),
                    "cost_basis": round(cumulative_cost, 2),
                    "unrealized_pnl": round(cumulative_pnl, 2),
                    "performance_pct": round(performance_pct, 2),
                    "total_trades": len(group),
                    "winning_trades": len(group[group['pnl'] > 0]),
                    "losing_trades": len(group[group['pnl'] < 0])
                })
            
            print(f"Calculated {len(daily_data)} days of performance data")
            
            # Show the data
            print("Performance progression:")
            for day in daily_data:
                print(f"  {day['date']}: ${day['total_value']:,.2f} ({day['performance_pct']:+.2f}%) - {day['total_trades']} trades")
            
            return daily_data
            
        else:
            print(f"Error getting trades: {response.text}")
            return []
            
    except Exception as e:
        print(f"Exception: {e}")
        return []

def update_performance_metrics(performance_data):
    """Update the performance_metrics table"""
    print("Updating performance metrics...")
    
    url = "https://injqbxdqyxfvannygadt.supabase.co/rest/v1/performance_metrics"
    headers = {
        "apikey": "SUPABASE_SECRET_KEY_REDACTED",
        "Authorization": "Bearer SUPABASE_SECRET_KEY_REDACTED",
        "Content-Type": "application/json"
    }
    
    # Clear existing data
    try:
        response = requests.delete(url + "?id=not.is.null", headers=headers)
        print(f"Cleared existing data: {response.status_code}")
    except Exception as e:
        print(f"Error clearing data: {e}")
    
    # Insert new data
    if performance_data:
        try:
            response = requests.post(url, headers=headers, json=performance_data)
            if response.status_code == 201:
                print(f"Successfully inserted {len(performance_data)} performance records")
                return True
            else:
                print(f"Error inserting data: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Exception inserting data: {e}")
            return False
    
    return False

if __name__ == "__main__":
    print("Trade-Based Performance Calculator")
    print("=" * 40)
    
    # Calculate performance from trades
    performance_data = calculate_performance_from_trades()
    
    if performance_data:
        # Update the database
        if update_performance_metrics(performance_data):
            print("\nReal performance data updated successfully!")
            print("The performance chart should now show your actual trading progression.")
        else:
            print("\nFailed to update performance data")
    else:
        print("\nNo performance data calculated")
