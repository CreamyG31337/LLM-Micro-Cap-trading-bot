-- =====================================================
-- CURRENCY PRE-CONVERSION SCHEMA
-- =====================================================
-- Adds support for pre-converting USD positions to base currency
-- This eliminates the need to fetch hundreds of exchange rates at runtime
-- Performance improvement: ~5-10s → <2s for 1-year dashboard loads
-- =====================================================

-- Add base_currency to funds table
-- This allows each fund to specify its display currency (CAD, USD, etc.)
ALTER TABLE funds ADD COLUMN IF NOT EXISTS base_currency VARCHAR(3) DEFAULT 'CAD';

-- Add pre-converted value columns to portfolio_positions
-- These store the position values converted to the fund's base currency
ALTER TABLE portfolio_positions 
  ADD COLUMN IF NOT EXISTS base_currency VARCHAR(3),
  ADD COLUMN IF NOT EXISTS total_value_base DECIMAL(15, 2),
  ADD COLUMN IF NOT EXISTS cost_basis_base DECIMAL(15, 2),
  ADD COLUMN IF NOT EXISTS pnl_base DECIMAL(15, 2),
  ADD COLUMN IF NOT EXISTS exchange_rate DECIMAL(10, 6);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_portfolio_positions_base_currency 
  ON portfolio_positions(base_currency);
  
CREATE INDEX IF NOT EXISTS idx_funds_base_currency 
  ON funds(base_currency);

-- Backfill base_currency for existing funds (default to CAD)
UPDATE funds SET base_currency = 'CAD' WHERE base_currency IS NULL;

-- =====================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================

COMMENT ON COLUMN funds.base_currency IS 
  'Base currency for displaying portfolio values (CAD, USD, etc.). Positions in other currencies are converted to this currency.';

COMMENT ON COLUMN portfolio_positions.base_currency IS 
  'Base currency used for this position snapshot (copied from fund settings)';

COMMENT ON COLUMN portfolio_positions.total_value_base IS 
  'Total market value converted to base currency (shares * price * exchange_rate)';

COMMENT ON COLUMN portfolio_positions.cost_basis_base IS 
  'Cost basis converted to base currency';

COMMENT ON COLUMN portfolio_positions.pnl_base IS 
  'P&L converted to base currency';

COMMENT ON COLUMN portfolio_positions.exchange_rate IS 
  'Exchange rate used for conversion (e.g., USD to CAD rate). 1.0 if no conversion needed.';

-- =====================================================
-- SCHEMA COMPLETE
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Currency pre-conversion schema created successfully!';
    RAISE NOTICE '📊 New columns added to portfolio_positions:';
    RAISE NOTICE '   - base_currency, total_value_base, cost_basis_base, pnl_base, exchange_rate';
    RAISE NOTICE '🏦 base_currency column added to funds table';
    RAISE NOTICE '📈 Next step: Run update_portfolio_prices job to populate new columns';
END $$;
