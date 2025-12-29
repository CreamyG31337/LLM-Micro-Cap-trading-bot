#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Review Script for Congress Trades Staging Batches
================================================================

Performs detailed data quality validation on staging batches before promotion.

Usage:
    python review_staging_batch.py <batch-id>
    python review_staging_batch.py --list  # List available batches
    python review_staging_batch.py --latest  # Review most recent batch
"""

import sys
import argparse
import io
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter, defaultdict
from datetime import datetime, date
import re

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from supabase_client import SupabaseClient
import pandas as pd

# Valid US state codes
VALID_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
}

VALID_PARTIES = {'Republican', 'Democrat', 'Independent'}
VALID_TYPES = {'Purchase', 'Sale', 'Exchange', 'Received'}
VALID_CHAMBERS = {'House', 'Senate'}


def get_available_batches(client: SupabaseClient) -> List[Dict[str, Any]]:
    """Get list of all available batches with metadata"""
    result = client.supabase.table('congress_trades_staging')\
        .select('import_batch_id, import_timestamp, validation_status, promoted_to_production')\
        .order('import_timestamp', desc=True)\
        .execute()
    
    # Group by batch_id
    batches = {}
    for row in result.data:
        batch_id = row['import_batch_id']
        if batch_id not in batches:
            batches[batch_id] = {
                'batch_id': batch_id,
                'import_timestamp': row['import_timestamp'],
                'validation_status': row.get('validation_status', 'pending'),
                'promoted_to_production': row.get('promoted_to_production', False)
            }
    
    # Get counts for each batch
    for batch_id in batches:
        count_result = client.supabase.table('congress_trades_staging')\
            .select('id', count='exact')\
            .eq('import_batch_id', batch_id)\
            .execute()
        batches[batch_id]['count'] = count_result.count or 0
    
    return list(batches.values())


def validate_ticker(ticker: str) -> bool:
    """Validate ticker symbol format (1-5 letters, optional numbers)"""
    if not ticker:
        return False
    # Ticker should be 1-5 characters, alphanumeric, typically uppercase
    return bool(re.match(r'^[A-Z0-9]{1,5}$', ticker.upper()))


def validate_politician_name(name: str) -> bool:
    """Validate politician name format (should have at least first and last name)"""
    if not name:
        return False
    parts = name.strip().split()
    return len(parts) >= 2  # At least first and last name


def validate_amount_format(amount: Optional[str]) -> bool:
    """Validate amount format (should be range like '$1,001 - $15,000' or similar)"""
    if not amount:
        return True  # Amount can be null
    # Check for common patterns: ranges, single values, etc.
    return bool(re.search(r'\$|USD|dollar', amount, re.IGNORECASE))


def check_completeness(df: pd.DataFrame) -> Dict[str, Any]:
    """Check data completeness"""
    total = len(df)
    if total == 0:
        return {
            'total': 0,
            'missing_party': 0,
            'missing_state': 0,
            'missing_owner': 0,
            'missing_ticker': 0,
            'missing_politician': 0,
            'missing_type': 0,
            'missing_chamber': 0,
            'missing_transaction_date': 0,
            'missing_disclosure_date': 0,
            'completeness_score': 0.0
        }
    
    missing_party = df['party'].isna().sum()
    missing_state = df['state'].isna().sum()
    missing_owner = df['owner'].isna().sum()
    missing_ticker = df['ticker'].isna().sum() | (df['ticker'] == '').sum()
    missing_politician = df['politician'].isna().sum() | (df['politician'] == '').sum()
    missing_type = df['type'].isna().sum()
    missing_chamber = df['chamber'].isna().sum()
    missing_transaction_date = df['transaction_date'].isna().sum()
    missing_disclosure_date = df['disclosure_date'].isna().sum()
    
    # Calculate completeness as percentage of non-missing critical fields
    # Critical fields: party, state, ticker, politician, type, chamber, transaction_date, disclosure_date
    # Owner is optional (can be NULL)
    critical_fields = 8
    total_critical_fields = total * critical_fields
    missing_critical = (missing_party + missing_state + missing_ticker + 
                       missing_politician + missing_type + missing_chamber + 
                       missing_transaction_date + missing_disclosure_date)
    
    completeness_score = 100 * (1 - missing_critical / total_critical_fields) if total_critical_fields > 0 else 0
    
    return {
        'total': total,
        'missing_party': int(missing_party),
        'missing_state': int(missing_state),
        'missing_owner': int(missing_owner),
        'missing_ticker': int(missing_ticker),
        'missing_politician': int(missing_politician),
        'missing_type': int(missing_type),
        'missing_chamber': int(missing_chamber),
        'missing_transaction_date': int(missing_transaction_date),
        'missing_disclosure_date': int(missing_disclosure_date),
        'completeness_score': round(completeness_score, 1)
    }


def check_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """Check data quality and validity"""
    issues = []
    warnings = []
    
    # Validate tickers
    invalid_tickers = []
    for idx, row in df.iterrows():
        if not validate_ticker(str(row['ticker'])):
            invalid_tickers.append((idx, row['ticker']))
    
    if invalid_tickers:
        issues.append(f"Invalid ticker symbols: {len(invalid_tickers)} found")
    
    # Validate politician names
    invalid_names = []
    for idx, row in df.iterrows():
        if not validate_politician_name(str(row['politician'])):
            invalid_names.append((idx, row['politician']))
    
    if invalid_names:
        issues.append(f"Invalid politician names: {len(invalid_names)} found")
    
    # Validate state codes
    invalid_states = df[df['state'].notna() & ~df['state'].isin(VALID_STATES)]
    if len(invalid_states) > 0:
        issues.append(f"Invalid state codes: {len(invalid_states)} found")
        warnings.append(f"Invalid states: {invalid_states['state'].unique().tolist()}")
    
    # Validate parties
    invalid_parties = df[df['party'].notna() & ~df['party'].isin(VALID_PARTIES)]
    if len(invalid_parties) > 0:
        issues.append(f"Invalid party values: {len(invalid_parties)} found")
        warnings.append(f"Invalid parties: {invalid_parties['party'].unique().tolist()}")
    
    # Validate transaction types
    invalid_types = df[~df['type'].isin(VALID_TYPES)]
    if len(invalid_types) > 0:
        issues.append(f"Invalid transaction types: {len(invalid_types)} found")
        warnings.append(f"Invalid types: {invalid_types['type'].unique().tolist()}")
    
    # Validate chambers
    invalid_chambers = df[~df['chamber'].isin(VALID_CHAMBERS)]
    if len(invalid_chambers) > 0:
        issues.append(f"Invalid chamber values: {len(invalid_chambers)} found")
        warnings.append(f"Invalid chambers: {invalid_chambers['chamber'].unique().tolist()}")
    
    # Check amount formats
    invalid_amounts = []
    for idx, row in df.iterrows():
        if row['amount'] and not validate_amount_format(row['amount']):
            invalid_amounts.append((idx, row['amount']))
    
    if invalid_amounts:
        warnings.append(f"Unusual amount formats: {len(invalid_amounts)} found")
    
    accuracy_score = 100 - (len(issues) * 20)  # Penalize 20 points per critical issue
    accuracy_score = max(0, accuracy_score)
    
    return {
        'issues': issues,
        'warnings': warnings,
        'invalid_tickers': invalid_tickers[:10],  # Limit to first 10
        'invalid_names': invalid_names[:10],
        'invalid_states': invalid_states[['politician', 'state']].to_dict('records')[:10] if len(invalid_states) > 0 else [],
        'invalid_parties': invalid_parties[['politician', 'party']].to_dict('records')[:10] if len(invalid_parties) > 0 else [],
        'invalid_types': invalid_types[['politician', 'type']].to_dict('records')[:10] if len(invalid_types) > 0 else [],
        'accuracy_score': round(accuracy_score, 1)
    }


def check_duplicates(df: pd.DataFrame) -> Dict[str, Any]:
    """Check for duplicates within batch"""
    # Create business key
    df['business_key'] = df.apply(lambda x: (
        str(x['politician']),
        str(x['ticker']),
        str(x['transaction_date']),
        str(x['type']),
        str(x.get('amount', '')),
        str(x.get('owner') or 'Not-Disclosed')
    ), axis=1)
    
    # Find duplicates
    duplicates = df[df.duplicated(subset='business_key', keep=False)]
    
    duplicate_groups = defaultdict(list)
    for idx, row in duplicates.iterrows():
        key = row['business_key']
        duplicate_groups[key].append({
            'id': row['id'],
            'politician': row['politician'],
            'ticker': row['ticker'],
            'transaction_date': str(row['transaction_date']),
            'type': row['type'],
            'amount': row.get('amount', ''),
            'owner': row.get('owner', 'Not-Disclosed')
        })
    
    return {
        'duplicate_count': len(duplicates),
        'duplicate_groups': len(duplicate_groups),
        'duplicate_examples': dict(list(duplicate_groups.items())[:5])  # First 5 groups
    }


def check_production_duplicates(client: SupabaseClient, df: pd.DataFrame) -> Dict[str, Any]:
    """Check if trades already exist in production"""
    # Get all production trades
    prod_result = client.supabase.table('congress_trades')\
        .select('politician, ticker, transaction_date, type, amount, owner')\
        .execute()
    
    if not prod_result.data:
        return {
            'production_count': 0,
            'duplicate_count': 0,
            'duplicate_percentage': 0.0
        }
    
    prod_df = pd.DataFrame(prod_result.data)
    
    # Create business keys for both
    df['business_key'] = df.apply(lambda x: (
        str(x['politician']),
        str(x['ticker']),
        str(x['transaction_date']),
        str(x['type']),
        str(x.get('amount', '')),
        str(x.get('owner') or 'Not-Disclosed')
    ), axis=1)
    
    prod_df['business_key'] = prod_df.apply(lambda x: (
        str(x['politician']),
        str(x['ticker']),
        str(x['transaction_date']),
        str(x['type']),
        str(x.get('amount', '')),
        str(x.get('owner') or 'Not-Disclosed')
    ), axis=1)
    
    # Find matches
    staging_keys = set(df['business_key'].unique())
    prod_keys = set(prod_df['business_key'].unique())
    duplicates = staging_keys & prod_keys
    
    return {
        'production_count': len(prod_df),
        'duplicate_count': len(duplicates),
        'duplicate_percentage': round(100 * len(duplicates) / len(df), 1) if len(df) > 0 else 0.0
    }


def generate_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate statistical analysis"""
    stats = {
        'total_trades': len(df),
        'party_breakdown': df['party'].value_counts().to_dict(),
        'chamber_breakdown': df['chamber'].value_counts().to_dict(),
        'type_breakdown': df['type'].value_counts().to_dict(),
        'top_tickers': df['ticker'].value_counts().head(10).to_dict(),
        'top_politicians': df['politician'].value_counts().head(10).to_dict(),
    }
    
    # Date range
    if df['transaction_date'].notna().any():
        stats['date_range'] = {
            'earliest': str(df['transaction_date'].min()),
            'latest': str(df['transaction_date'].max())
        }
    else:
        stats['date_range'] = None
    
    # Owner breakdown
    stats['owner_breakdown'] = df['owner'].value_counts().to_dict() if df['owner'].notna().any() else {}
    
    return stats


def detect_anomalies(df: pd.DataFrame) -> List[str]:
    """Detect unusual patterns"""
    anomalies = []
    
    # Multiple trades by same person on same day
    same_day_trades = df.groupby(['politician', 'transaction_date']).size()
    high_frequency = same_day_trades[same_day_trades > 10]
    if len(high_frequency) > 0:
        anomalies.append(f"{len(high_frequency)} politicians with 10+ trades on same day")
    
    # Missing owner but other fields filled
    missing_owner_filled = df[(df['owner'].isna()) & (df['politician'].notna()) & (df['ticker'].notna())]
    if len(missing_owner_filled) > 0:
        anomalies.append(f"{len(missing_owner_filled)} trades with missing owner (acceptable, will default)")
    
    # Unusual ticker patterns
    ticker_lengths = df['ticker'].str.len()
    unusual_tickers = df[(ticker_lengths > 5) | (ticker_lengths < 1)]
    if len(unusual_tickers) > 0:
        anomalies.append(f"{len(unusual_tickers)} trades with unusual ticker lengths")
    
    return anomalies


def review_batch(client: SupabaseClient, batch_id: str) -> Dict[str, Any]:
    """Perform comprehensive review of a staging batch"""
    
    # Get batch data with pagination (Supabase has 1000 row limit per request)
    print(f"Fetching all trades for batch {batch_id}...")
    all_trades = []
    batch_size = 1000
    offset = 0
    
    while True:
        result = client.supabase.table('congress_trades_staging')\
            .select('*')\
            .eq('import_batch_id', batch_id)\
            .range(offset, offset + batch_size - 1)\
            .execute()
        
        if not result.data:
            break
        
        all_trades.extend(result.data)
        
        # If we got fewer rows than batch_size, we're done
        if len(result.data) < batch_size:
            break
        
        offset += batch_size
        
        # Safety break to prevent infinite loops
        if offset > 100000:  # Allow up to 100k rows
            print(f"Warning: Reached 100,000 row safety limit")
            break
        
        # Progress indicator
        if offset % 5000 == 0:
            print(f"  Fetched {len(all_trades)} rows so far...")
    
    print(f"Total rows fetched: {len(all_trades)}\n")
    
    if not all_trades:
        return {'error': f"No data found for batch {batch_id}"}
    
    trades = all_trades
    df = pd.DataFrame(trades)
    
    # Perform all checks
    completeness = check_completeness(df)
    quality = check_data_quality(df)
    duplicates = check_duplicates(df)
    prod_duplicates = check_production_duplicates(client, df)
    statistics = generate_statistics(df)
    anomalies = detect_anomalies(df)
    
    # Calculate overall scores
    consistency_score = 100.0
    if duplicates['duplicate_count'] > 0:
        consistency_score -= min(30, duplicates['duplicate_groups'] * 5)
    
    overall_score = (
        completeness['completeness_score'] * 0.4 +
        quality['accuracy_score'] * 0.4 +
        consistency_score * 0.2
    )
    
    # Determine status
    critical_issues = []
    missing_party_trades = []
    if completeness['missing_party'] > 0:
        missing_party_df = df[df['party'].isna()]
        missing_party_trades = missing_party_df[['id', 'politician', 'ticker', 'transaction_date', 'chamber', 'state']].to_dict('records')[:20]  # Limit to first 20
        critical_issues.append(f"Missing party for {completeness['missing_party']} trades")
    if completeness['missing_state'] > 0:
        critical_issues.append(f"Missing state for {completeness['missing_state']} trades")
    if quality['invalid_tickers']:
        critical_issues.append(f"Invalid ticker symbols: {len(quality['invalid_tickers'])}")
    if quality['invalid_names']:
        critical_issues.append(f"Invalid politician names: {len(quality['invalid_names'])}")
    if quality['issues']:
        critical_issues.extend(quality['issues'])
    
    if critical_issues:
        status = "NEEDS REVIEW"
    elif duplicates['duplicate_count'] > 0 or quality['warnings']:
        status = "APPROVE WITH REVIEW"
    else:
        status = "READY TO PROMOTE"
    
    return {
        'batch_id': batch_id,
        'status': status,
        'completeness': completeness,
        'quality': quality,
        'duplicates': duplicates,
        'production_duplicates': prod_duplicates,
        'statistics': statistics,
        'anomalies': anomalies,
        'scores': {
            'completeness': completeness['completeness_score'],
            'accuracy': quality['accuracy_score'],
            'consistency': round(consistency_score, 1),
            'overall': round(overall_score, 1)
        },
        'critical_issues': critical_issues,
        'warnings': quality['warnings'],
        'missing_party_trades': missing_party_trades,
        'import_timestamp': trades[0].get('import_timestamp') if trades else None
    }


def print_report(review: Dict[str, Any]):
    """Print comprehensive review report"""
    if 'error' in review:
        print(f"❌ {review['error']}")
        return
    
    print("\n" + "="*80)
    print("CONGRESS TRADES STAGING BATCH REVIEW")
    print("="*80)
    print(f"\nBatch ID: {review['batch_id']}")
    if review.get('import_timestamp'):
        print(f"Import Time: {review['import_timestamp']}")
    
    # Executive Summary
    print("\n" + "-"*80)
    print("EXECUTIVE SUMMARY")
    print("-"*80)
    print(f"Overall Assessment: {review['status']}")
    print(f"Total Trades in Batch: {review['completeness']['total']}")
    print(f"Critical Issues: {len(review['critical_issues'])}")
    print(f"Warnings: {len(review['warnings'])}")
    
    # Data Quality Score
    print("\n" + "-"*80)
    print("DATA QUALITY SCORE")
    print("-"*80)
    scores = review['scores']
    print(f"Completeness: {scores['completeness']}/100")
    print(f"Accuracy: {scores['accuracy']}/100")
    print(f"Consistency: {scores['consistency']}/100")
    print(f"Overall: {scores['overall']}/100")
    
    # Detailed Findings
    print("\n" + "-"*80)
    print("DETAILED FINDINGS")
    print("-"*80)
    
    # Passing Checks
    print("\n✅ Passing Checks:")
    passing = []
    if review['completeness']['missing_party'] == 0:
        passing.append("All trades have party information")
    if review['completeness']['missing_state'] == 0:
        passing.append("All trades have state information")
    if review['completeness']['missing_ticker'] == 0:
        passing.append("All trades have ticker symbols")
    if review['completeness']['missing_politician'] == 0:
        passing.append("All trades have politician names")
    if review['duplicates']['duplicate_count'] == 0:
        passing.append("No duplicates within batch")
    if not review['quality']['issues']:
        passing.append("All data validation checks passed")
    
    if passing:
        for check in passing:
            print(f"  • {check}")
    else:
        print("  (No checks passed)")
    
    # Warnings
    if review['warnings']:
        print("\n⚠️  Warnings:")
        for warning in review['warnings']:
            print(f"  • {warning}")
    
    if review['duplicates']['duplicate_count'] > 0:
        print(f"\n⚠️  Duplicates within batch: {review['duplicates']['duplicate_count']} trades in {review['duplicates']['duplicate_groups']} groups")
        if review['duplicates']['duplicate_examples']:
            print("  Example duplicate groups:")
            for i, (key, records) in enumerate(list(review['duplicates']['duplicate_examples'].items())[:3], 1):
                print(f"    {i}. {records[0]['politician']} | {records[0]['ticker']} | {records[0]['transaction_date']} ({len(records)} records)")
    
    if review['production_duplicates']['duplicate_count'] > 0:
        print(f"\nℹ️  Production Duplicates: {review['production_duplicates']['duplicate_count']} trades ({review['production_duplicates']['duplicate_percentage']}%) already exist in production")
        print("  (These will be automatically skipped during promotion)")
    
    if review['anomalies']:
        print("\n⚠️  Anomalies Detected:")
        for anomaly in review['anomalies']:
            print(f"  • {anomaly}")
    
    # Critical Issues
    if review['critical_issues']:
        print("\n❌ Critical Issues:")
        for issue in review['critical_issues']:
            print(f"  • {issue}")
        
        if review['quality']['invalid_tickers']:
            print("\n  Invalid Ticker Examples:")
            for idx, ticker in review['quality']['invalid_tickers'][:5]:
                print(f"    - Row {idx}: '{ticker}'")
        
        if review['quality']['invalid_names']:
            print("\n  Invalid Name Examples:")
            for idx, name in review['quality']['invalid_names'][:5]:
                print(f"    - Row {idx}: '{name}'")
        
        if review['quality']['invalid_states']:
            print("\n  Invalid State Examples:")
            for record in review['quality']['invalid_states'][:5]:
                print(f"    - {record['politician']}: '{record['state']}'")
        
        if review['quality']['invalid_parties']:
            print("\n  Invalid Party Examples:")
            for record in review['quality']['invalid_parties'][:5]:
                print(f"    - {record['politician']}: '{record['party']}'")
        
        if review.get('missing_party_trades'):
            print("\n  Missing Party Examples (first 20):")
            for trade in review['missing_party_trades'][:10]:
                print(f"    - ID {trade['id']}: {trade['politician']} | {trade['ticker']} | {trade['transaction_date']} | Chamber: {trade.get('chamber', 'N/A')} | State: {trade.get('state', 'N/A')}")
    
    # Recommendations
    print("\n" + "-"*80)
    print("RECOMMENDATIONS")
    print("-"*80)
    
    if review['critical_issues']:
        print("\n1. Immediate Actions Required:")
        print("   • Fix all critical issues before promotion")
        if review['completeness']['missing_party'] > 0:
            print("   • Populate missing party information")
        if review['completeness']['missing_state'] > 0:
            print("   • Populate missing state information")
        if review['quality']['invalid_tickers']:
            print("   • Fix or remove invalid ticker symbols")
        if review['quality']['invalid_names']:
            print("   • Fix malformed politician names")
    
    if review['warnings'] or review['duplicates']['duplicate_count'] > 0:
        print("\n2. Suggested Fixes:")
        if review['duplicates']['duplicate_count'] > 0:
            print("   • Review and remove duplicate trades within batch")
        if review['warnings']:
            print("   • Review warnings and fix data quality issues")
    
    print("\n3. Promotion Decision:")
    if review['status'] == "READY TO PROMOTE":
        print("   ✅ APPROVE for promotion to production")
    elif review['status'] == "APPROVE WITH REVIEW":
        print("   ⚠️  APPROVE with manual review of flagged items")
    else:
        print("   ❌ REJECT - fix issues and re-import")
    
    # Supporting Data
    print("\n" + "-"*80)
    print("SUPPORTING DATA")
    print("-"*80)
    
    stats = review['statistics']
    print(f"\nTotal Trades: {stats['total_trades']}")
    
    if stats['date_range']:
        print(f"Date Range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
    
    print("\nBreakdown by Party:")
    for party, count in stats['party_breakdown'].items():
        print(f"  {party or 'NULL'}: {count}")
    
    print("\nBreakdown by Chamber:")
    for chamber, count in stats['chamber_breakdown'].items():
        print(f"  {chamber}: {count}")
    
    print("\nBreakdown by Transaction Type:")
    for ttype, count in stats['type_breakdown'].items():
        print(f"  {ttype}: {count}")
    
    print("\nTop 5 Most-Traded Tickers:")
    for ticker, count in list(stats['top_tickers'].items())[:5]:
        print(f"  {ticker}: {count} trades")
    
    print("\nTop 5 Politicians by Trade Count:")
    for politician, count in list(stats['top_politicians'].items())[:5]:
        print(f"  {politician}: {count} trades")
    
    if stats['owner_breakdown']:
        print("\nBreakdown by Owner:")
        for owner, count in list(stats['owner_breakdown'].items())[:5]:
            print(f"  {owner or 'NULL'}: {count}")
    
    print("\n" + "="*80)
    print()


def main():
    parser = argparse.ArgumentParser(description='Review congress trades staging batch')
    parser.add_argument('batch_id', nargs='?', help='Batch ID to review')
    parser.add_argument('--list', action='store_true', help='List available batches')
    parser.add_argument('--latest', action='store_true', help='Review most recent batch')
    
    args = parser.parse_args()
    
    client = SupabaseClient(use_service_role=True)
    
    if args.list:
        print("\nAvailable Batches:")
        print("-"*80)
        batches = get_available_batches(client)
        for batch in batches:
            status_icon = "✅" if batch['promoted_to_production'] else "⏳"
            print(f"{status_icon} {batch['batch_id']}")
            print(f"   Count: {batch['count']} trades")
            print(f"   Imported: {batch['import_timestamp']}")
            print(f"   Status: {batch['validation_status']}")
            print()
        return
    
    if args.latest:
        batches = get_available_batches(client)
        if not batches:
            print("❌ No batches found in staging")
            return
        batch_id = batches[0]['batch_id']
        print(f"Reviewing latest batch: {batch_id}\n")
    elif args.batch_id:
        batch_id = args.batch_id
    else:
        print("Error: Must provide batch_id, --list, or --latest")
        parser.print_help()
        sys.exit(1)
    
    review = review_batch(client, batch_id)
    print_report(review)


if __name__ == '__main__':
    main()

