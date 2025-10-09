#!/usr/bin/env python3
"""
Fund Contributors Migration Script
==================================

Migrates fund contribution data (contributors/holders) from CSV to Supabase.

This migrates the fund_contributions.csv files which contain:
- Contributor names and emails
- Contribution and withdrawal amounts
- Transaction timestamps and notes

Usage:
    python migrate_contributors.py [--fund FUND_NAME] [--dry-run]
"""

import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from web_dashboard.supabase_client import SupabaseClient


class ContributorMigrator:
    """Handles migration of fund contributor data from CSV to Supabase"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = None
        self.migration_stats = {
            'funds_processed': 0,
            'funds_successful': 0,
            'funds_failed': 0,
            'total_contributions': 0,
            'errors': []
        }
        
    def initialize_client(self) -> bool:
        """Initialize Supabase client"""
        try:
            self.client = SupabaseClient()
            if self.client.test_connection():
                print("✅ Supabase connection successful")
                return True
            else:
                print("❌ Supabase connection failed")
                return False
        except Exception as e:
            print(f"❌ Failed to initialize Supabase client: {e}")
            return False
    
    def get_available_csv_funds(self) -> List[str]:
        """Get list of funds with CSV data"""
        funds_dir = Path("trading_data/funds")
        available_funds = []
        
        for fund_dir in funds_dir.iterdir():
            if fund_dir.is_dir():
                contrib_file = fund_dir / "fund_contributions.csv"
                if contrib_file.exists():
                    available_funds.append(fund_dir.name)
        
        return available_funds
    
    def load_contributions(self, fund_name: str) -> Optional[pd.DataFrame]:
        """Load fund contributions from CSV"""
        fund_dir = Path("trading_data/funds") / fund_name
        contrib_file = fund_dir / "fund_contributions.csv"
        
        if not contrib_file.exists():
            print(f"  ⚠️  No fund_contributions.csv found for {fund_name}")
            return None
        
        try:
            df = pd.read_csv(contrib_file)
            
            # Ensure required columns exist
            required_cols = ['Timestamp', 'Contributor', 'Amount', 'Type']
            if not all(col in df.columns for col in required_cols):
                print(f"  ❌ Missing required columns in {fund_name} contributions")
                return None
            
            # Add Email and Notes columns if missing
            if 'Email' not in df.columns:
                df['Email'] = ''
            if 'Notes' not in df.columns:
                df['Notes'] = ''
            
            # Parse timestamps - handle mixed formats
            try:
                # Try parsing with timezone first
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], utc=True)
            except:
                # If that fails, try without timezone
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
                # Fill any NaT values with current time
                df['Timestamp'] = df['Timestamp'].fillna(pd.Timestamp.now())
            
            return df
            
        except Exception as e:
            print(f"  ❌ Error loading contributions for {fund_name}: {e}")
            return None
    
    def migrate_contributions(self, fund_name: str, df: pd.DataFrame) -> bool:
        """Migrate fund contributions to Supabase"""
        if df is None or df.empty:
            print(f"  ⚠️  No contributions to migrate for {fund_name}")
            return False
        
        print(f"  📊 Migrating {len(df)} contributions")
        
        # Convert DataFrame to list of dicts for Supabase
        contributions = []
        for _, row in df.iterrows():
            contribution = {
                'fund': fund_name,
                'contributor': str(row['Contributor']),
                'email': str(row.get('Email', '')) if pd.notna(row.get('Email')) else '',
                'amount': float(row['Amount']),
                'contribution_type': str(row['Type']).upper(),  # CONTRIBUTION or WITHDRAWAL
                'timestamp': row['Timestamp'].isoformat(),
                'notes': str(row.get('Notes', '')) if pd.notna(row.get('Notes')) else ''
            }
            contributions.append(contribution)
        
        if self.dry_run:
            print(f"  🔍 [DRY RUN] Would migrate {len(contributions)} contributions")
            return True
        
        # Insert into Supabase
        try:
            # Delete existing contributions for this fund first
            self.client.supabase.table('fund_contributions').delete().eq('fund', fund_name).execute()
            print(f"  🗑️  Cleared existing contributions for {fund_name}")
            
            # Insert new contributions
            result = self.client.supabase.table('fund_contributions').insert(contributions).execute()
            print(f"  ✅ Successfully migrated {len(contributions)} contributions")
            
            self.migration_stats['total_contributions'] += len(contributions)
            return True
            
        except Exception as e:
            error_msg = f"{fund_name}: Contributions migration error - {e}"
            print(f"  ❌ {error_msg}")
            self.migration_stats['errors'].append(error_msg)
            return False
    
    def migrate_fund(self, fund_name: str) -> bool:
        """Migrate contributor data for a single fund"""
        print(f"\n👥 Migrating Contributors: {fund_name}")
        print("=" * 50)
        
        self.migration_stats['funds_processed'] += 1
        
        # Load contributions
        df = self.load_contributions(fund_name)
        
        if df is None or df.empty:
            print(f"  ⚠️  No contributor data found for {fund_name}")
            return False
        
        # Display summary
        total_contributions = df[df['Type'] == 'CONTRIBUTION']['Amount'].sum()
        total_withdrawals = df[df['Type'] == 'WITHDRAWAL']['Amount'].sum() if 'WITHDRAWAL' in df['Type'].values else 0
        net_capital = total_contributions - total_withdrawals
        unique_contributors = df['Contributor'].nunique()
        
        print(f"  📈 {unique_contributors} unique contributors")
        print(f"  💰 Total contributions: ${total_contributions:,.2f}")
        print(f"  💸 Total withdrawals: ${total_withdrawals:,.2f}")
        print(f"  💵 Net capital: ${net_capital:,.2f}")
        
        # Migrate
        success = self.migrate_contributions(fund_name, df)
        
        if success:
            print(f"  🎉 Successfully migrated contributors for {fund_name}")
            self.migration_stats['funds_successful'] += 1
        else:
            print(f"  ❌ Migration failed for {fund_name}")
            self.migration_stats['funds_failed'] += 1
        
        return success
    
    def print_migration_summary(self):
        """Print migration summary"""
        print("\n" + "=" * 50)
        print("📊 MIGRATION SUMMARY")
        print("=" * 50)
        print(f"Funds Processed: {self.migration_stats['funds_processed']}")
        print(f"✅ Successful: {self.migration_stats['funds_successful']}")
        print(f"❌ Failed: {self.migration_stats['funds_failed']}")
        print(f"📝 Total Contributions Migrated: {self.migration_stats['total_contributions']}")
        
        if self.migration_stats['errors']:
            print(f"\n⚠️  Errors ({len(self.migration_stats['errors'])}):")
            for error in self.migration_stats['errors']:
                print(f"  - {error}")
        
        print("=" * 50)
        
        if self.migration_stats['funds_successful'] > 0:
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        else:
            print("❌ MIGRATION FAILED - No funds migrated")


def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description="Migrate fund contributors to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without actually doing it")
    parser.add_argument("--fund", type=str, help="Migrate only a specific fund")
    
    args = parser.parse_args()
    
    print("🚀 Fund Contributors Migration to Supabase")
    print("=" * 40)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No actual changes will be made")
    
    # Initialize migrator
    migrator = ContributorMigrator(dry_run=args.dry_run)
    
    # Initialize Supabase connection
    if not migrator.initialize_client():
        print("❌ Cannot proceed without Supabase connection")
        return 1
    
    # Get available funds
    available_funds = migrator.get_available_csv_funds()
    if not available_funds:
        print("❌ No funds with contributor data found")
        return 1
    
    print(f"📂 Found {len(available_funds)} funds with contributor data: {', '.join(available_funds)}")
    
    # Filter to specific fund if requested
    if args.fund:
        if args.fund not in available_funds:
            print(f"❌ Fund '{args.fund}' not found or has no contributor data")
            return 1
        available_funds = [args.fund]
        print(f"🎯 Migrating only: {args.fund}")
    
    # Confirm migration
    if not args.dry_run:
        print(f"\n⚠️  This will REPLACE existing contributor data in Supabase for {len(available_funds)} fund(s)")
        confirmation = input("Continue? (yes/no): ").strip().lower()
        if confirmation not in ['yes', 'y']:
            print("Migration cancelled")
            return 0
    
    # Migrate each fund
    for fund_name in available_funds:
        migrator.migrate_fund(fund_name)
    
    # Print summary
    migrator.print_migration_summary()
    
    return 0 if migrator.migration_stats['funds_failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

