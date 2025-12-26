-- =====================================================
-- EXCHANGE RATE LOOKUP FUNCTION
-- =====================================================
-- Helper function for get_exchange_rate_for_date
-- Used by backfill_preconverted_values function
-- =====================================================

CREATE OR REPLACE FUNCTION get_exchange_rate_for_date(
    rate_date TIMESTAMP,
    from_currency VARCHAR(3),
    to_currency VARCHAR(3)
) RETURNS NUMERIC AS $$
DECLARE
    found_rate NUMERIC;
BEGIN
    -- Look up exchange rate for the given date and currency pair
    SELECT rate INTO found_rate
    FROM exchange_rates
    WHERE DATE(date) = DATE(rate_date)
        AND UPPER(from_curr) = UPPER(from_currency)
        AND UPPER(to_curr) = UPPER(to_currency)
    ORDER BY date DESC
    LIMIT 1;
    
    -- Return the rate (NULL if not found, caller handles fallback)
    RETURN found_rate;
END;
$$ LANGUAGE plpgsql STABLE
SET search_path = public;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION get_exchange_rate_for_date(TIMESTAMP, VARCHAR, VARCHAR) TO service_role;
GRANT EXECUTE ON FUNCTION get_exchange_rate_for_date(TIMESTAMP, VARCHAR, VARCHAR) TO authenticated;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Exchange rate lookup function created successfully!';
    RAISE NOTICE '📊 Function: get_exchange_rate_for_date(date, from_curr, to_curr)';
    RAISE NOTICE '🔍 Returns: exchange rate as NUMERIC (NULL if not found)';
END $$;
