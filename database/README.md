# Database Schema

This folder contains all SQL scripts for database setup and maintenance.

## 🏗️ Fresh Database Setup

Run these scripts **in order** in Supabase SQL Editor:

1. `setup/01_tables.sql` - Core tables (portfolio_positions, trade_log)
2. `setup/02_auth.sql` - Authentication schema
3. `setup/03_securities.sql` - Securities lookup table
4. `setup/04_thesis.sql` - Fund thesis table
5. `setup/05_contributions.sql` - Fund contributions
6. `setup/06_exchange_rates.sql` - Exchange rates table
7. `setup/07_views.sql` - Optimized views (latest_positions, current_positions, etc.)

## 🔧 Data Fixes (DF_)

One-time fixes applied to resolve issues. Prefixed with `DF_` and numbered:

| File | Description | Applied |
|------|-------------|---------|
| `DF_001_fix_latest_positions_view.sql` | Fix daily P&L calculation in view | ✅ |
| `DF_002_fix_country_column.sql` | Fix country column in securities | ✅ |
| `DF_003_fix_contributors_rls.sql` | Fix RLS for contributions table | ❓ |
| `DF_004_fix_user_setup.sql` | Fix user authentication setup | ❓ |
| `DF_005_clean_trade_log_add_fk.sql` | Add FK constraints to trade_log | ✅ |

## ⚙️ Utilities

Helper scripts for development:

- `disable_all_rls.sql` - Disable Row Level Security (dev only!)
- `disable_rls_single_user.sql` - RLS config for single-user mode
- `sample_data.sql` - Insert test/sample data
- `relational_design_docs.sql` - Schema documentation

## 📁 Archive

Old migrations kept for reference. These have already been applied and shouldn't be run again.
