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

**Important**: These fixes are required when installing the app from scratch. After running the schema files in `setup/`, run all `DF_*.sql` files in the `fixes/` folder in numerical order.

One-time fixes applied to resolve issues. Prefixed with `DF_` and numbered:

| File | Description | Applied |
|------|-------------|---------|
| `DF_001_fix_latest_positions_view.sql` | Fix daily P&L calculation in view | ✅ |
| `DF_002_fix_country_column.sql` | Fix country column in securities | ✅ |
| `DF_003_fix_contributors_rls.sql` | Fix RLS for contributions table | ❓ |
| `DF_004_fix_user_setup.sql` | Fix user authentication setup | ❓ |
| `DF_005_clean_trade_log_add_fk.sql` | Add FK constraints to trade_log | ✅ |
| `DF_006_enable_rls_fix.sql` | Enable RLS on tables | ✅ |
| `DF_007_add_securities_to_latest_positions.sql` | Add securities to latest positions view | ✅ |
| `DF_007_fix_unregistered_contributors.sql` | Fix unregistered contributors | ✅ |
| `DF_008_add_thesis_view.sql` | Add thesis view | ✅ |
| `DF_008_fix_daily_pnl_lookback.sql` | Fix daily P&L lookback | ✅ |
| `DF_008_link_fund_contributions_to_funds.sql` | Link fund contributions to funds table | ✅ |
| `DF_009_create_contributors_and_access.sql` | Create contributors and access tables | ✅ |
| `DF_010_update_rls_for_contributors.sql` | Update RLS for contributors | ✅ |
| `DF_011_update_contributor_ownership_view.sql` | Update contributor ownership view | ✅ |
| `DF_012_verify_contributors_table.sql` | Verify contributors table | ✅ |
| `DF_013_fix_rpc_permissions.sql` | Fix RPC permissions | ✅ |
| `DF_014_fix_rls_auth_users.sql` | Fix RLS for auth users | ✅ |
| `DF_015_fix_fund_contribution_rls.sql` | Fix fund contribution RLS | ✅ |
| `DF_016_fix_fund_data_rls.sql` | Fix fund data RLS | ✅ |

## 🐛 Debug Scripts

Diagnostic and debugging SQL scripts located in `debug/` folder. These are **not** required for fresh installs:

- `check_emails.sql` - Check email-related data
- `check_fund_dates.sql` - Verify fund date ranges
- `check_view_output.sql` - Test view outputs
- `debug_user_metrics.sql` - Debug user metrics calculations
- `delete_dec23_positions.sql` - Cleanup script for December 2023 positions
- `diagnose_daily_pnl.sql` - Diagnose daily P&L issues
- `fix_benchmark_data_rls.sql` - Fix benchmark data RLS (debug only)
- `verify_fix.sql` - Verify fix application

## ⚙️ Utilities

Helper scripts for development:

- `disable_all_rls.sql` - Disable Row Level Security (dev only!)
- `disable_rls_single_user.sql` - RLS config for single-user mode
- `sample_data.sql` - Insert test/sample data
- `relational_design_docs.sql` - Schema documentation

## 📁 Archive

Old migrations kept for reference. These have already been applied and shouldn't be run again.
