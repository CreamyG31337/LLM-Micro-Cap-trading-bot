# Trading Bot Test Issues Todo List

## High Priority

- [ ] **Fix TradeProcessor decimal.ConversionSyntax error in _update_position_after_buy method** (IN PROGRESS)
- [ ] **Resolve FIFO system tests failing due to insufficient shares (5/7 tests failing)**

## Medium Priority

- [ ] **Fix CSV timestamp format consistency problems across repositories**
- [ ] **Resolve cash balance inconsistencies in financial calculations**
- [ ] **Fix concurrent data access simulation failures in integration tests**
- [ ] **Resolve repository factory creation errors in integration tests**

## Low Priority

- [ ] **Fix menu integration execution errors (prompt generator and cash updates)**
- [ ] **Resolve migration preparation test issues (data migration and filtering)**

## Summary
- **Total Issues**: 8
- **High Priority**: 2 (TradeProcessor decimal error, FIFO tests)
- **Medium Priority**: 4 (Integration test failures)
- **Low Priority**: 2 (Menu and migration tests)
- **Status**: ~30-40 failing tests out of 244 total, with decimal transition causing many float-to-decimal mismatches

## Notes
- TradeProcessor error is the main blocker preventing FIFO tests from working
- Many test failures likely due to transition from floats to decimals for money values
- Tests may need updates to work with corrected decimal implementation

---

## Daily Prompt Enhancements — Portfolio Manager Requests (2025-09-14)

Goal: Add company profile and fundamentals to the daily prompt, prioritizing items available via API or straightforward computation. Place fields into existing tables when they fit; otherwise, introduce a third "Fundamentals" table with both rich and plain-text fallbacks.

### Placement plan (initial)
- Price & Volume table: Add Avg Volume (30d), 52-Week High, 52-Week Low (width permitting)
- Snapshot table: Add % of Portfolio
- New Fundamentals table: Sector, Industry/Theme, Country, Market Cap, P/E (TTM), Dividend Yield

### High Priority (API-available or computed)
- [ ] % of Portfolio
  - Placement: Snapshot table (new column after Total Value)
  - Source: Computed = position_value / total_portfolio_value
  - Notes: Format to one decimal place (e.g., 12.3%)
  - Acceptance: Each row shows % of portfolio for the position

- [ ] Avg Volume (30 day)
  - Placement: Price & Volume table (new column)
  - Source: Compute from historical data last 30 trading days (market_data_fetcher); fallback to API field (e.g., averageVolume, averageDailyVolume3Month)
  - Notes: Prefer compute to be consistent; unit: shares (no decimals). Handle thinly traded tickers.
  - Acceptance: Column displays a reasonable 30-day average volume value

- [ ] 52-Week High
  - Placement: Price & Volume table (if width allows) or Fundamentals table
  - Source: API field (fiftyTwoWeekHigh) or compute from last ~252 trading days OHLC
  - Acceptance: Value present for equities; ETFs okay when available

- [ ] 52-Week Low
  - Placement: Price & Volume table (if width allows) or Fundamentals table
  - Source: API field (fiftyTwoWeekLow) or compute from last ~252 trading days OHLC
  - Acceptance: Value present for equities; ETFs okay when available

- [ ] Sector
  - Placement: Fundamentals table
  - Source: API profile (e.g., assetProfile.sector)
  - Acceptance: Displays sector string or N/A when unavailable (e.g., for some ETFs)

- [ ] Industry
  - Placement: Fundamentals table
  - Source: API profile (e.g., assetProfile.industry)
  - Acceptance: Displays industry string or N/A

- [ ] Country
  - Placement: Fundamentals table
  - Source: API profile (country); fallback rule: .TO => Canada, else USA if unknown
  - Acceptance: Displays country string

- [ ] Market Cap
  - Placement: Fundamentals table
  - Source: API quote/price summary (marketCap)
  - Notes: Format with suffixes (e.g., $1.23B)
  - Acceptance: Shows numeric market cap or N/A

- [ ] P/E Ratio (TTM)
  - Placement: Fundamentals table
  - Source: API (trailingPE); if negative earnings or missing, show N/A
  - Acceptance: Numeric ratio with one decimal or N/A

- [ ] Dividend Yield
  - Placement: Fundamentals table
  - Source: API (dividendYield or trailingAnnualDividendYield)
  - Notes: Format as percent with one decimal (e.g., 2.1%)
  - Acceptance: Percent or N/A

### Medium Priority / Requires mapping or curation
- [ ] Theme (e.g., Gold Mining, Semiconductors, Uranium Miners, Enterprise Software)
  - Placement: Fundamentals table (paired with Industry)
  - Source: Not reliably provided by most APIs; derive via curated mapping by ticker/industry keywords; start with simple rules, extend over time
  - Acceptance: Reasonable theme label or N/A; ensure maintainable mapping config

### Plumbing & implementation tasks
- [ ] Add fundamentals fetcher with caching
  - Implement market_data_fetcher.fetch_fundamentals(ticker) returning: sector, industry, country, marketCap, trailingPE, dividendYield, 52w high/low, avg volume fields
  - Use lightweight provider (e.g., yfinance) and add TTL cache to reduce calls and avoid rate limits

- [ ] Compute 30-day average volume if not available
  - Use historical daily volume series; compute mean over last 30 trading days with missing data handling

- [ ] Extend prompt layout
  - Add % of Portfolio column to Snapshot
  - Add 52-Week High/Low and Avg Volume (30d) to Price & Volume where width allows; otherwise move to Fundamentals
  - Add new Fundamentals table displayed alongside Snapshot/Ownership in rich mode; plain text fallback for simple consoles

- [ ] Formatting & fallbacks
  - Human-friendly number formatting (k/M/B suffixes)
  - Graceful N/A handling (ETFs, missing fields)
  - Maintain color conventions; avoid ANSI in raw values used by LLMs

- [ ] Tests
  - Unit tests for fundamentals fetch and formatting
  - Snapshot/Price&Volume table render tests (rich and plain)
  - Caching behavior tests and API fallback paths

- [ ] Config & performance
  - Add toggle to enable/disable Fundamentals table and optional columns
  - Respect API rate limits; batch-fetch when possible; log warnings on failures

### Acceptance (end-to-end)
- New fields appear in the daily prompt in their designated places with correct formatting
- Works for both U.S. and TSX tickers; missing data handled gracefully
- No significant slowdown in prompt generation (caching enabled)
- Rich and plain-text modes both render cleanly
