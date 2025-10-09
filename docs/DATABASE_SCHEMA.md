# Supabase Database Schema Documentation

## Overview
The trading bot uses Supabase as the primary database for portfolio and trade data. This document outlines the current schema and provides optimized views for P&L calculations.

**Last Updated:** 2025-10-07  
**Optimization Status:** Views now pre-calculate `market_value` in the database for improved performance

## Tables

### 1. portfolio_positions
Stores individual position records with current market data.

**Schema:**
```sql
CREATE TABLE portfolio_positions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    fund VARCHAR(50) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    company VARCHAR(255),  -- Company name for display
    shares DECIMAL(15, 6) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,  -- Current market price
    cost_basis DECIMAL(10, 2) NOT NULL,  -- Total cost basis
    pnl DECIMAL(10, 2) NOT NULL DEFAULT 0,  -- Unrealized P&L
    total_value DECIMAL(10, 2) GENERATED ALWAYS AS (shares * price) STORED,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    date TIMESTAMP WITH TIME ZONE NOT NULL,  -- Snapshot timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    unrealized_pnl DECIMAL(10, 2) DEFAULT 0,
    stop_loss DECIMAL(10, 2) DEFAULT NULL,
    current_price DECIMAL(10, 2) DEFAULT NULL,
    avg_price DECIMAL(10, 2) GENERATED ALWAYS AS (cost_basis / NULLIF(shares, 0)) STORED
);
```

**Sample Record:**
```json
{
  "id": "88beb32b-1b82-45ce-ac0d-fb1e9fb10f1f",
  "fund": "Test Fund",
  "ticker": "AAPL",
  "shares": 10.0,
  "price": 150.0,
  "cost_basis": 1500.0,
  "pnl": 0.0,
  "total_value": 1500.0,
  "currency": "USD",
  "date": "2025-10-03T00:17:26.525243+00:00",
  "company": "Apple Inc."
}
```

### 2. trade_log
Stores individual trade transactions.

**Schema:**
```sql
CREATE TABLE trade_log (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    fund VARCHAR(50) NOT NULL,
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    shares DECIMAL(15, 6) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    cost_basis DECIMAL(10, 2) NOT NULL,
    pnl DECIMAL(10, 2) NOT NULL DEFAULT 0,
    reason VARCHAR(255),
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Sample Record:**
```json
{
  "id": "2aa5f3f9-f65a-44ac-bd62-402359cf9e4a",
  "fund": "Project Chimera",
  "date": "2025-09-08T13:30:00+00:00",
  "ticker": "CTRN",
  "shares": 9.2961,
  "price": 37.65,
  "cost_basis": 350.0,
  "pnl": 0.0,
  "reason": "MANUAL BUY MOO - Filled",
  "currency": "USD"
}
```

### 3. fund_contributions
Stores individual contribution and withdrawal transactions for fund contributors/holders.

**Schema:**
```sql
CREATE TABLE fund_contributions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    fund VARCHAR(50) NOT NULL,
    contributor VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    amount DECIMAL(10, 2) NOT NULL,
    contribution_type VARCHAR(20) NOT NULL, -- CONTRIBUTION or WITHDRAWAL
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Sample Record:**
```json
{
  "id": "3bb6f4a0-f65a-44ac-bd62-402359cf9e4b",
  "fund": "Project Chimera",
  "contributor": "Lance Colton",
  "email": "lance.colton@gmail.com",
  "amount": 1000.0,
  "contribution_type": "CONTRIBUTION",
  "timestamp": "2025-09-08T21:59:48+00:00",
  "notes": ""
}
```

**Note:** Contributors (holders) are different from dashboard users:
- **Contributors**: Investors who have put money into the fund (tracked in `fund_contributions`)
- **Dashboard Users**: People who can log in to view the dashboard (tracked in `user_profiles`)

## Views

### contributor_ownership
Aggregates contributions and withdrawals to show current ownership:
```sql
CREATE VIEW contributor_ownership AS
SELECT 
    fund,
    contributor,
    email,
    SUM(CASE WHEN contribution_type = 'CONTRIBUTION' THEN amount ELSE 0 END) as total_contributions,
    SUM(CASE WHEN contribution_type = 'WITHDRAWAL' THEN amount ELSE 0 END) as total_withdrawals,
    SUM(CASE 
        WHEN contribution_type = 'CONTRIBUTION' THEN amount 
        WHEN contribution_type = 'WITHDRAWAL' THEN -amount 
        ELSE 0 
    END) as net_contribution,
    COUNT(*) as transaction_count,
    MIN(timestamp) as first_contribution,
    MAX(timestamp) as last_transaction
FROM fund_contributions
GROUP BY fund, contributor, email;
```

### fund_contributor_summary
Provides fund-level contributor statistics:
```sql
CREATE VIEW fund_contributor_summary AS
SELECT 
    fund,
    COUNT(DISTINCT contributor) as total_contributors,
    SUM(CASE WHEN contribution_type = 'CONTRIBUTION' THEN amount ELSE 0 END) as total_contributions,
    SUM(CASE WHEN contribution_type = 'WITHDRAWAL' THEN amount ELSE 0 END) as total_withdrawals,
    SUM(CASE 
        WHEN contribution_type = 'CONTRIBUTION' THEN amount 
        WHEN contribution_type = 'WITHDRAWAL' THEN -amount 
        ELSE 0 
    END) as net_capital,
    MIN(timestamp) as fund_inception,
    MAX(timestamp) as last_activity
FROM fund_contributions
GROUP BY fund;
```

## Current Issues

### 1. Duplicate Entries Problem
- **Issue**: Multiple entries per ticker per day with different timestamps
- **Cause**: Portfolio update mechanism creating new snapshots instead of updating existing ones
- **Impact**: 405+ duplicate entries from single day, incorrect P&L calculations

### 2. P&L Calculation Issues
- **Issue**: P&L not being calculated correctly in database
- **Need**: Server-side P&L calculation using views
- **Solution**: Create views that calculate unrealized P&L automatically

## Proposed Views for P&L Calculation

### 1. Current Positions View
```sql
CREATE VIEW current_positions AS
SELECT 
    fund,
    ticker,
    company,
    shares,
    price as current_price,
    cost_basis,
    (shares * price) as market_value,
    (shares * price - cost_basis) as unrealized_pnl,
    currency,
    date as last_updated
FROM portfolio_positions
WHERE date = (
    SELECT MAX(date) 
    FROM portfolio_positions p2 
    WHERE p2.fund = portfolio_positions.fund 
    AND p2.ticker = portfolio_positions.ticker
);
```

### 2. Daily P&L Summary View
```sql
CREATE VIEW daily_pnl_summary AS
SELECT 
    fund,
    DATE(date) as trade_date,
    COUNT(DISTINCT ticker) as positions_count,
    SUM(shares * price) as total_market_value,
    SUM(cost_basis) as total_cost_basis,
    SUM(shares * price - cost_basis) as total_unrealized_pnl,
    AVG((shares * price - cost_basis) / NULLIF(cost_basis, 0)) * 100 as avg_return_pct
FROM portfolio_positions
GROUP BY fund, DATE(date)
ORDER BY trade_date DESC;
```

### 3. Trade Performance View
```sql
CREATE VIEW trade_performance AS
SELECT 
    t.fund,
    t.ticker,
    t.date as trade_date,
    t.shares,
    t.price as trade_price,
    t.cost_basis,
    p.price as current_price,
    (p.price - t.price) * t.shares as price_change_pnl,
    ((p.price - t.price) / t.price) * 100 as return_percentage
FROM trade_log t
LEFT JOIN current_positions p ON t.ticker = p.ticker AND t.fund = p.fund
WHERE t.shares > 0;  -- Only buy transactions
```

## Next Steps

1. **Clean Database**: Remove duplicate entries
2. **Create Views**: Implement P&L calculation views
3. **Test Views**: Verify calculations match CSV data
4. **Update Application**: Use views for P&L display
5. **Debug Duplicates**: Fix portfolio update mechanism
6. **Migrate Contributors**: Run `python web_dashboard/migrate_contributors.py` to populate fund_contributions table

## Migrating Contributors/Holders

To migrate fund contributor data from CSV files to Supabase:

```bash
# First, create the table by running the SQL schema in Supabase
# web_dashboard/schema/05_fund_contributions_schema.sql

# Then migrate the data
python web_dashboard/migrate_contributors.py --fund "Project Chimera"

# Or migrate all funds
python web_dashboard/migrate_contributors.py
```

See `web_dashboard/CONTRIBUTORS_MIGRATION.md` for detailed migration instructions.
