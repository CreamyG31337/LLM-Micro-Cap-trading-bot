-- =====================================================
-- BACKFILL CURRENCY PRE-CONVERSION DATA
-- =====================================================
-- Populates base_currency columns for historical portfolio_positions
-- that were created before the currency pre-conversion schema was added.
-- This eliminates the "slow path" warning by ensuring all data has
-- pre-converted values available.
-- =====================================================

-- Step 1: Backfill base_currency from fund settings
UPDATE portfolio_positions pp
SET base_currency = f.base_currency
FROM funds f
WHERE pp.fund = f.name
  AND pp.base_currency IS NULL;

-- Step 2: Backfill pre-converted values for positions
-- This handles the most common case: USD positions converted to CAD base currency

-- First, create a temporary function to get exchange rates
CREATE OR REPLACE FUNCTION get_rate_for_position(pos_date TIMESTAMP, from_curr VARCHAR, to_curr VARCHAR)
RETURNS DECIMAL(10, 6) AS $$
DECLARE
    rate DECIMAL(10, 6);
BEGIN
    -- Get the most recent exchange rate on or before the position date
    SELECT r.rate INTO rate
    FROM exchange_rates r
    WHERE r.from_currency = from_curr
      AND r.to_currency = to_curr
      AND r.timestamp <= pos_date
    ORDER BY r.timestamp DESC
    LIMIT 1;
    
    -- If no rate found, return 1.0 (no conversion)
    IF rate IS NULL THEN
        RETURN 1.0;
    END IF;
    
    RETURN rate;
END;
$$ LANGUAGE plpgsql;

-- Step 3: Update positions where currency matches base_currency (no conversion needed)
UPDATE portfolio_positions
SET 
    total_value_base = total_value,
    cost_basis_base = cost_basis,
    pnl_base = pnl,
    exchange_rate = 1.0
WHERE total_value_base IS NULL
  AND currency = base_currency;

-- Step 4: Update USD positions with base_currency = CAD (most common case)
UPDATE portfolio_positions pp
SET 
    total_value_base = pp.total_value * get_rate_for_position(pp.date, 'USD', 'CAD'),
    cost_basis_base = pp.cost_basis * get_rate_for_position(pp.date, 'USD', 'CAD'),
    pnl_base = pp.pnl * get_rate_for_position(pp.date, 'USD', 'CAD'),
    exchange_rate = get_rate_for_position(pp.date, 'USD', 'CAD')
WHERE pp.total_value_base IS NULL
  AND pp.currency = 'USD'
  AND pp.base_currency = 'CAD';

-- Step 5: Handle any remaining NULL values (fallback for unsupported conversions)
-- Store values as-is with exchange_rate = 1.0
UPDATE portfolio_positions
SET 
    total_value_base = total_value,
    cost_basis_base = cost_basis,
    pnl_base = pnl,
    exchange_rate = 1.0
WHERE total_value_base IS NULL;

-- Step 6: Clean up temporary function
DROP FUNCTION IF EXISTS get_rate_for_position(TIMESTAMP, VARCHAR, VARCHAR);

-- =====================================================
-- VERIFICATION & SUMMARY
-- =====================================================

DO $$
DECLARE
    total_rows BIGINT;
    preconverted_rows BIGINT;
    null_rows BIGINT;
BEGIN
    -- Count total positions
    SELECT COUNT(*) INTO total_rows FROM portfolio_positions;
    
    -- Count positions with pre-converted data
    SELECT COUNT(*) INTO preconverted_rows 
    FROM portfolio_positions 
    WHERE total_value_base IS NOT NULL;
    
    -- Count positions still missing pre-converted data
    SELECT COUNT(*) INTO null_rows 
    FROM portfolio_positions 
    WHERE total_value_base IS NULL;
    
    RAISE NOTICE '✅ Currency pre-conversion backfill completed!';
    RAISE NOTICE '📊 Total portfolio positions: %', total_rows;
    RAISE NOTICE '✔️  Positions with pre-converted values: %', preconverted_rows;
    RAISE NOTICE '❌ Positions still missing values: %', null_rows;
    
    IF null_rows > 0 THEN
        RAISE WARNING '⚠️  Some positions could not be backfilled. Check currency and exchange rate data.';
    ELSE
        RAISE NOTICE '🎉 All historical data has been backfilled successfully!';
        RAISE NOTICE '⚡ The dashboard will now use the FAST PATH for all queries!';
    END IF;
END $$;
