-- Fix metadata for Canadian ETFs that yfinance doesn't have good data for
-- These are manually curated based on the ETF's actual holdings

UPDATE securities 
SET 
    sector = 'Energy',
    industry = 'Uranium Mining ETF',
    country = 'Global',
    last_updated = NOW()
WHERE ticker = 'HURA.TO';

UPDATE securities 
SET 
    sector = 'Materials',
    industry = 'Lithium Producers ETF',
    country = 'Global',
    last_updated = NOW()
WHERE ticker = 'HLIT.TO';

UPDATE securities 
SET 
    sector = 'Emerging Markets',
    industry = 'China Equity ETF',
    country = 'China',
    last_updated = NOW()
WHERE ticker = 'ZCH.TO';

-- Verify the updates
SELECT ticker, company_name, sector, industry, country 
FROM securities 
WHERE ticker IN ('HURA.TO', 'HLIT.TO', 'ZCH.TO');
