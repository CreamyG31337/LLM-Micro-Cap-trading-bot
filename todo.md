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

---

## Email Trade Ingestion Improvements (Option 'e') — Plan (2025-09-14)

Goals:
- Allow entering multiple email trades in one session with per-trade confirmation
- Append parsed trades to trade log (canonical), not directly to portfolio snapshot
- After user is done, offer to rebuild portfolio from trade log
- Use caching to minimize repeated API calls (company names, prices)

Tasks:
- [x] Add multi-email interactive mode to add_trade_from_email.py with END/DONE flow
- [x] Confirm each parsed trade before saving; display parsed details clearly
- [x] Save to trade log only; avoid immediate portfolio mutation to preserve invariants
- [x] Prompt to rebuild portfolio after session; wire to debug/rebuild_portfolio_from_scratch.py
- [x] Convert rebuild script to use cached MarketDataFetcher + PriceCache
- [x] Add company name caching using PriceCache; persist cache for reuse
- [x] Add idempotency: prevent duplicate trades by de-duplicating on (timestamp,ticker,action,shares,price)
- [ ] Optional: CLI flag to auto-rebuild after N trades without prompt
- [ ] Optional: Batch prefetch prices for tickers present in the session to accelerate rebuild

Documentation & Tests:
- [x] Add docs/EMAIL_INGEST.md covering workflow, idempotency, caching, and usage
- [ ] Add unit tests for is_duplicate_trade() with edge cases (timestamps, rounding)
- [ ] Add integration test for add_trade_from_email multi-email flow (mock input)

Acceptance:
- User can paste multiple emails and save multiple trades in one run
- Trade log shows appended entries; portfolio not directly modified during ingestion
- Rebuild prompt runs and regenerates portfolio correctly
- Company names and price/history requests hit caches on subsequent runs

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

---

## Performance Graph Enhancement Ideas (2025-09-15)

### Quick Visual Wins
- [ ] Add weekend/holiday shading and market-open bands for clearer temporal context
- [ ] Shade "outperformance region" between portfolio and benchmark when portfolio is above/below SPX
- [ ] Add a second small subplot for drawdown (area below zero), or a panel of daily returns bars (green/red)
- [ ] Place a horizontal zero line for performance (100 index) and horizontal max drawdown line for context
- [ ] Improve legend to show final returns inline (e.g., Portfolio +0.54%, S&P +X.YZ%)
- [ ] Auto-avoid label clipping: dynamic offsets and use annotate with bbox for all callouts
- [ ] Tight titles: title = Performance, subtitle = invested amount and timeframe

### Analytics and Truth-in-Performance
- [ ] Time-weighted return (TWR) as primary performance metric (neutralizes cash flows)
- [ ] Money-weighted return (IRR/XIRR) as a secondary metric
- [ ] Cumulative contributions line/series and a PnL-only line (market value − contributions)
- [ ] Rolling metrics: 3/5/10-day rolling return, volatility; simple Sharpe/Sortino (pick a risk-free)
- [ ] Peak/valley markers for max drawdown and time-to-recover from drawdown (TTR)
- [ ] Per-position contribution to portfolio PnL (stacked bar inset or table export)
- [ ] Optional second benchmark (e.g., equal-weighted index, sector ETF) for context

### Data Handling and Correctness
- [ ] Lock all calculations to Decimal (only cast to float right at plotting) to respect your precision rule
- [ ] Cache S&P data locally (CSV in trading_data cache) to avoid repeated downloads and reduce flakiness
- [ ] Robust yfinance fallback (retry, then flat-line placeholder with a warning)
- [ ] Optional timezone normalization and weekend-forward-fill toggle
- [ ] Strict alignment: reindex benchmark to portfolio dates with forward-fill, baseline both at portfolio start

### Interactivity and Exports
- [ ] Optional interactive Plotly export (hover tooltips for points and annotations)
- [ ] Export both PNG and SVG (sharp in docs) plus a thumbnail (1200x675 social)
- [ ] Emit a CSV of computed series (Date, Performance_Index, Drawdown, SPX_Index, Contributions, PnL)
- [ ] Optional PDF report with a one-page summary (metrics + charts)

### CLI Ergonomics
- [ ] --start-date, --end-date, --benchmark ^GSPC, --no-weekends, --no-annotations
- [ ] --format png|svg|pdf, --dpi 200/300, --figsize 16x9, --output-dir Results/
- [ ] --metrics-only (no chart; prints JSON/CSV of metrics)
- [ ] --second-benchmark TICKER for dual benchmarks

### Readability Polish
- [ ] Consistent color semantics: portfolio=blue, benchmark=orange, drawdown=red
- [ ] Dynamic y-limits with margins so annotations never hug edges
- [ ] Smart date formatting (monthly ticks if long span; daily if short)
- [ ] Show market-closure notes in footer when forward-filling was applied

### Validation and Tests
- [ ] Add a tiny test portfolio fixture with known TWR/Drawdown to snapshot-test outputs
- [ ] Unit tests for date alignment, baseline normalization, forward-fill logic, Decimal math

### Nice-to-Haves
- [ ] Regime shading (bull/bear bands) based on moving averages of benchmark
- [ ] Label significant events (big buys/sells) as small markers with hover (in interactive mode)
- [ ] Option to show cumulative alpha (portfolio minus benchmark) as a line or separate subplot

### Implementation Bundles:
- **"Metrics + Drawdown"**: Add TWR as the performance line, plus a PnL line, and a drawdown subplot
- **"Benchmarks + Cache"**: Add a second benchmark flag and caching for SPX
- **"Exports + CLI flags"**: Export SVG + CSV alongside PNG with CLI options

---

## Interactive Web Dashboard Migration (Vercel + Supabase) (2025-09-15)

### Vision: Advanced Interactive Portfolio Analytics
Move from static Python charts to a modern web dashboard with real-time interactivity, user authentication, and cloud deployment.

### Core Interactive Features
- [ ] **Toggle Individual Holdings**: Interactive chart where users can show/hide specific tickers
- [ ] **Multi-timeframe Analysis**: Switch between 1D, 1W, 1M, 3M, YTD, 1Y views
- [ ] **Benchmark Switching**: Toggle between S&P 500, Russell 2000, sector ETFs, custom benchmarks
- [ ] **Performance Attribution**: See which holdings contributed most to gains/losses
- [ ] **Risk Metrics Dashboard**: Real-time Sharpe ratio, volatility, beta calculations
- [ ] **Portfolio Rebalancing Simulator**: "What-if" scenarios for position sizing changes

### Technology Stack

#### Frontend (Next.js + Vercel)
- [ ] **Next.js 14** with App Router for modern React framework
- [ ] **Recharts or Chart.js** for interactive financial charts with hover/zoom/pan
- [ ] **Tailwind CSS** for responsive design and dark/light theme toggle
- [ ] **shadcn/ui** components for professional dashboard UI
- [ ] **React Query (TanStack Query)** for data fetching and caching
- [ ] **Zustand** for client-side state management (chart settings, filters)

#### Backend (Supabase)
- [ ] **Supabase Database**: PostgreSQL with real-time subscriptions
- [ ] **Row Level Security (RLS)**: Multi-user support with private portfolio data
- [ ] **Supabase Auth**: Google/GitHub OAuth + email/password authentication
- [ ] **Edge Functions**: Serverless functions for complex calculations (TWR, risk metrics)
- [ ] **Supabase Storage**: File uploads for trade logs, CSV imports

#### Data Pipeline
- [ ] **Real-time Price Updates**: Schedule Edge Functions to update prices every 15min during market hours
- [ ] **Market Data APIs**: Integrate with Alpha Vantage, Polygon.io, or IEX Cloud
- [ ] **Currency Conversion**: Auto-convert USD/CAD positions with live FX rates
- [ ] **Historical Data**: Import existing CSV data to Supabase tables

### Database Schema Design

#### Core Tables
- [ ] **users**: User profiles and settings
- [ ] **portfolios**: Multiple portfolios per user (Paper, Real, Archive)
- [ ] **positions**: Current holdings with cost basis, shares, market value
- [ ] **trades**: Complete trade history with FIFO processing
- [ ] **market_data**: Cached price/volume data to reduce API calls
- [ ] **benchmarks**: S&P 500, sector indices for comparison
- [ ] **cash_flows**: Deposits, withdrawals, dividend payments

#### Advanced Tables
- [ ] **portfolio_snapshots**: Daily portfolio valuations for time series
- [ ] **risk_metrics**: Pre-calculated Sharpe, beta, volatility by date
- [ ] **alerts**: Price alerts, rebalancing suggestions, performance notifications
- [ ] **watchlists**: Tickers users want to track for future investment

### Interactive Chart Features

#### Core Interactivity
- [ ] **Holding Toggle Checkboxes**: Show/hide individual tickers with smooth animation
- [ ] **Performance Mode Switching**: Total return vs individual position returns
- [ ] **Benchmark Overlay**: Multiple benchmarks on same chart with different colors
- [ ] **Date Range Picker**: Custom start/end dates with preset shortcuts
- [ ] **Zoom and Pan**: Mouse wheel zoom, drag to pan time series
- [ ] **Hover Tooltips**: Show exact values, dates, holding details on mouseover

#### Advanced Interactions
- [ ] **Crossfilter Integration**: Selecting a date highlights all positions on that date
- [ ] **Performance Attribution Bars**: Stacked bars showing which holdings drove daily returns
- [ ] **Correlation Matrix**: Heatmap showing how holdings move relative to each other
- [ ] **Risk-Return Scatter**: Plot holdings by volatility vs return with bubble sizes = position size
- [ ] **Drawdown Waterfall**: Visualize how each holding contributed to portfolio drawdowns
- [ ] **Sector/Geography Breakdown**: Pie charts and treemaps for portfolio composition

### User Experience Features

#### Portfolio Management
- [ ] **Multiple Portfolio Support**: Paper trading, different strategies, archived portfolios
- [ ] **CSV Import/Export**: Upload trade logs, export performance reports
- [ ] **Trade Entry Interface**: Clean forms for adding new trades with auto-completion
- [ ] **Position Sizing Calculator**: Suggest position sizes based on portfolio % or risk parity
- [ ] **Rebalancing Alerts**: Notify when positions drift from target allocations

#### Reporting and Analytics
- [ ] **PDF Performance Reports**: Monthly/quarterly reports with charts and key metrics
- [ ] **Email Digest**: Weekly performance summary with top movers
- [ ] **Custom Dashboards**: User-configurable widgets and chart layouts
- [ ] **Benchmark Comparison Tables**: Side-by-side performance vs multiple indices
- [ ] **Tax Reporting**: Realized gains/losses with wash sale detection

#### Social/Collaboration
- [ ] **Portfolio Sharing**: Public/private portfolio links with configurable privacy
- [ ] **Community Leaderboards**: Anonymous performance rankings (opt-in)
- [ ] **Discussion Integration**: Comments on trades, market observations

### Migration Strategy

#### Phase 1: Core Infrastructure
- [ ] Set up Vercel project with Next.js 14
- [ ] Configure Supabase project with authentication
- [ ] Design and implement core database schema
- [ ] Migrate existing CSV data to Supabase tables
- [ ] Build basic user registration/login flow

#### Phase 2: Basic Dashboard
- [ ] Create main portfolio overview page
- [ ] Implement basic interactive chart with Recharts
- [ ] Add portfolio performance metrics display
- [ ] Build trade entry and editing interface
- [ ] Implement CSV import for historical data

#### Phase 3: Advanced Analytics
- [ ] Add individual holding toggle functionality
- [ ] Implement multiple benchmark comparisons
- [ ] Build risk metrics calculations (Edge Functions)
- [ ] Add performance attribution analysis
- [ ] Create advanced chart types (correlation, scatter)

#### Phase 4: Polish and Scale
- [ ] Implement real-time price updates
- [ ] Add mobile-responsive design
- [ ] Build PDF reporting system
- [ ] Optimize performance and caching
- [ ] Add comprehensive error handling and monitoring

### Technical Considerations

#### Performance Optimization
- [ ] **Chart Data Virtualization**: Handle large time series efficiently
- [ ] **Incremental Static Regeneration**: Cache heavy calculations at build time
- [ ] **Edge Caching**: Cache market data and calculations globally
- [ ] **Lazy Loading**: Load chart components only when needed
- [ ] **Database Indexing**: Optimize queries for time series and user filtering

#### Security and Privacy
- [ ] **End-to-end Encryption**: Sensitive portfolio data encrypted at rest
- [ ] **API Rate Limiting**: Prevent abuse of market data endpoints
- [ ] **Input Validation**: Sanitize all user inputs and CSV uploads
- [ ] **Audit Logging**: Track all portfolio modifications for debugging
- [ ] **GDPR Compliance**: Data export and deletion capabilities

#### Monitoring and Reliability
- [ ] **Error Tracking**: Sentry integration for bug monitoring
- [ ] **Performance Monitoring**: Vercel Analytics and Core Web Vitals
- [ ] **Uptime Monitoring**: Health checks for critical functions
- [ ] **Backup Strategy**: Regular database backups with point-in-time recovery
- [ ] **Market Data Fallbacks**: Multiple data sources to handle API outages

### Success Metrics
- Users can toggle individual holdings on/off with sub-second response time
- Charts handle 1000+ data points smoothly on mobile devices
- 99.9% uptime during market hours
- Support for 10+ concurrent users without performance degradation
- Real-time updates reflect within 30 seconds of market data changes

### Timeline Estimate
- **Phase 1 (Infrastructure)**: 2-3 weeks
- **Phase 2 (Basic Dashboard)**: 3-4 weeks
- **Phase 3 (Advanced Analytics)**: 4-6 weeks
- **Phase 4 (Polish)**: 2-3 weeks
- **Total**: 11-16 weeks for full migration

---

## Portfolio Maintenance Architecture (2025-09-15)

### Current State: Rebuild Script as Temporary Solution
The `debug/rebuild_portfolio_from_scratch.py` script is currently necessary because the main application doesn't maintain the portfolio CSV properly during normal operations. This creates data inconsistencies that require periodic rebuilding.

### Long-term Goal: Eliminate Need for Rebuild Script
The application should maintain portfolio data integrity in real-time, eliminating the need for manual rebuilds.

### Tasks:
- [ ] **Improve Portfolio CSV Maintenance**: Ensure the main trading script properly updates portfolio CSV during all operations
- [ ] **Real-time Data Consistency**: Fix any data inconsistencies that occur during normal trading operations
- [ ] **Automatic Validation**: Add built-in validation to catch and prevent data corruption
- [ ] **Incremental Updates**: Make portfolio updates incremental rather than requiring full rebuilds
- [ ] **Error Recovery**: Add automatic error recovery for common data issues
- [ ] **Deprecate Rebuild Script**: Once portfolio maintenance is robust, mark rebuild script as deprecated

### Technical Requirements:
- Portfolio CSV should always reflect current state without manual intervention
- All trade operations should maintain data integrity
- System should handle edge cases gracefully (weekends, holidays, API failures)
- Performance should not degrade with portfolio size
- Data validation should catch issues before they require rebuilds

### Success Criteria:
- Portfolio CSV remains consistent through all normal operations
- No manual rebuilds required for data integrity
- Rebuild script becomes optional maintenance tool only
- System handles all edge cases automatically

---

## Fund Contributor Email Enhancement (2025-09-14)

### Goals:
- Capture contributor email addresses when adding fund contributions
- Add menu option to edit contributor names and emails
- Maintain backward compatibility with existing contributor data

### Tasks:
- [ ] Update fund_contributions.csv schema to include Email column
- [ ] Modify log_contribution() method to capture email addresses
- [ ] Modify log_withdrawal() method to capture email addresses
- [ ] Add manage_contributors() method for editing contributor info
- [ ] Add 'Manage Contributors' menu option to trading script
- [ ] Test new contributor management functionality

### Implementation Details:
- Email field should be optional for backward compatibility
- Existing contributors without emails should show as "Not provided"
- Menu option 'm' will be added for 'Manage Contributors'
- Contributors should be editable by name lookup

### Acceptance Criteria:
- Users can add fund contributions with email addresses
- Users can edit existing contributor names and emails
- System gracefully handles contributors without email data
- CSV format remains compatible with existing data
