# Prompt for LLM Review of Congress Trades Staging Data

You are reviewing congressional stock trading data that has been scraped and imported into a staging table before being promoted to production. Your task is to validate the data quality and identify any issues that need to be addressed.

## Context

The data comes from the `congress_trades_staging` table and represents stock trades by U.S. Congress members. Each import batch has a unique `import_batch_id` (UUID). The data must be validated before being promoted to the production `congress_trades` table.

## Your Task

Review the staging batch and provide a detailed assessment of data quality, completeness, and any issues that need attention.

## Data Schema

Each trade record contains:
- **politician**: Full name of the Congress member
- **ticker**: Stock ticker symbol (e.g., NVDA, AAPL)
- **transaction_date**: Date the trade was executed
- **disclosure_date**: Date the trade was publicly disclosed
- **type**: Transaction type (Purchase, Sale, Exchange, Received)
- **amount**: Trade amount as a range (e.g., "$1,001 - $15,000")
- **chamber**: House or Senate
- **party**: Political party (Democrat, Republican, Independent)
- **state**: 2-letter state code (e.g., CA, NY, PA)
- **owner**: Asset owner (Self, Spouse, Joint, Child, Not-Disclosed)
- **price**: Stock price at time of trade (optional)
- **asset_type**: Type of asset (Stock, Crypto)
- **raw_data**: Original JSON from scraper (for debugging)

## How to Access the Data

You have access to a Python environment with the following already configured:

```python
import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

# Get the batch data
batch_id = "REPLACE_WITH_BATCH_ID"
result = client.supabase.table('congress_trades_staging')\
    .select('*')\
    .eq('import_batch_id', batch_id)\
    .execute()

trades = result.data
```

## Validation Checklist

### 1. Data Completeness
Check for missing or null values in critical fields:
- [ ] Are any `party` fields missing?
- [ ] Are any `state` fields missing?
- [ ] Are any `owner` fields missing? (NULL is acceptable, will default to 'Not-Disclosed')
- [ ] Are all `ticker` symbols present and valid (1-5 letters)?
- [ ] Are all dates properly formatted?

### 2. Data Quality
Check for data anomalies:
- [ ] Are politician names properly formatted (First Last)?
- [ ] Are state codes valid 2-letter abbreviations?
- [ ] Are party values limited to (Democrat, Republican, Independent)?
- [ ] Are transaction types limited to (Purchase, Sale, Exchange, Received)?
- [ ] Are amount ranges in standard format?
- [ ] Are there any suspicious patterns (same person, same stock, same day with identical amounts)?

### 3. Duplicate Detection
Check for duplicates within the batch:
- [ ] Are there any exact duplicates (same politician, ticker, date, type, amount, owner)?
- [ ] Are there near-duplicates that might indicate data issues?

The business key for detecting duplicates is:
```python
(politician, ticker, transaction_date, type, amount, owner)
```

### 4. Cross-Reference with Production
Check if these trades already exist in production:
- [ ] How many trades in this batch already exist in `congress_trades`?
- [ ] Should duplicates with production be flagged or are they expected?

### 5. Statistical Analysis
Provide insights on the batch:
- [ ] Total number of trades
- [ ] Breakdown by party (Democrat, Republican, Independent)
- [ ] Breakdown by chamber (House, Senate)
- [ ] Breakdown by transaction type (Purchase vs Sale)
- [ ] Top 5 most-traded tickers in this batch
- [ ] Top 5 politicians by number of trades
- [ ] Date range of trades in this batch

### 6. Anomaly Detection
Flag any unusual patterns:
- [ ] Trades with unusually high/low amounts
- [ ] Multiple trades by same person on same day
- [ ] Trades in unusual tickers (verify they're real stocks)
- [ ] Trades with missing owner but filled in other fields
- [ ] Any trades from politicians not typically seen

## Sample Analysis Code

```python
import pandas as pd
from collections import Counter, defaultdict

df = pd.DataFrame(trades)

# Completeness check
print("Data Completeness:")
print(f"  Total trades: {len(df)}")
print(f"  Missing party: {df['party'].isna().sum()}")
print(f"  Missing state: {df['state'].isna().sum()}")
print(f"  Missing owner: {df['owner'].isna().sum()}")

# Duplicate detection
df['key'] = df.apply(lambda x: (
    x['politician'], x['ticker'], 
    str(x['transaction_date']), x['type'], 
    x['amount'], x.get('owner')
), axis=1)
duplicates = df[df.duplicated(subset='key', keep=False)]

if len(duplicates) > 0:
    print(f"\n⚠️  Found {len(duplicates)} duplicate trades")
    print(duplicates[['politician', 'ticker', 'transaction_date', 'type']])

# Statistical breakdown
print("\nBreakdown by Party:")
print(df['party'].value_counts())

print("\nTop 5 Tickers:")
print(df['ticker'].value_counts().head())

print("\nTop 5 Politicians:")
print(df['politician'].value_counts().head())
```

## Your Report Format

Provide your assessment in this format:

### Executive Summary
- Overall assessment: READY TO PROMOTE / NEEDS REVIEW / REJECT
- Total trades in batch: X
- Critical issues: X
- Warnings: X

### Data Quality Score
- Completeness: X/100
- Accuracy: X/100  
- Consistency: X/100
- Overall: X/100

### Detailed Findings

#### ✅ Passing Checks
- List checks that passed

#### ⚠️ Warnings
- List non-critical issues that should be noted

#### ❌ Critical Issues
- List blocking issues that prevent promotion

### Recommendations

1. **Immediate Actions Required** (if any critical issues)
2. **Suggested Fixes**
3. **Promotion Decision**: 
   - [ ] APPROVE for promotion to production
   - [ ] APPROVE with manual review of flagged items
   - [ ] REJECT - fix issues and re-import

### Supporting Data

Provide relevant tables, charts, or statistics that support your findings.

## Important Notes

- **NULL values for `owner`**: These are acceptable and will be defaulted to 'Not-Disclosed' during promotion
- **Duplicates with production**: These will be automatically skipped during promotion, so they're not blocking issues
- **Focus on data integrity**: The main concern is ensuring politician names, parties, states are accurate
- **Raw data field**: If you find issues, reference the `raw_data` JSON field to understand what the scraper captured

## Example Issues to Flag

**Critical:**
- Missing `party` or `state` for active Congress members
- Invalid ticker symbols (not 1-5 letters)
- Malformed politician names (missing first or last name)
- Invalid state codes (not in standard US state list)

**Warning:**
- Missing `owner` field (acceptable, but note it)
- Duplicate trades within batch (could indicate scraper issue)
- Unusual trading patterns (100+ trades from one person)

**Info:**
- Duplicates with production (will be auto-skipped)
- Date range of import
- Distribution statistics

Begin your review now. Be thorough but concise in your findings.
