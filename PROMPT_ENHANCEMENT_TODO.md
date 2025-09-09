# Prompt Generator Enhancement TODO

## 🎯 **IMMEDIATE PRIORITY** (New Portfolio - 3 Positions)
*Focus on features that provide immediate value for a small, new portfolio*

### ✅ **Quick Wins** (1-2 hours implementation)
- [x] **Daily P&L Calculation** ✅ **COMPLETED**
  - [x] Fixed daily P&L showing "N/A" by expanding date range
  - [x] Implemented industry-standard close-to-close calculation
  - [x] Added proper market hours handling
  - [x] Documented design and implementation

- [ ] **Enhanced Position Performance Display**
  - [ ] Add individual position P&L percentages
  - [ ] Show position performance vs. buy price
  - [ ] Display unrealized gains/losses clearly
  - [ ] Add position weight as % of total portfolio

- [ ] **Basic Risk Metrics**
  - [ ] Portfolio concentration analysis (top position %)
  - [ ] Individual position risk scores (volatility)
  - [ ] Simple drawdown calculation
  - [ ] Cash allocation percentage

- [ ] **Improved Market Data**
  - [ ] Add 5-day performance for each position
  - [ ] Show volume trends (current vs. average)
  - [ ] Add simple moving averages (5-day, 20-day)
  - [ ] Include sector information for each holding

### 🔧 **Medium Priority** (3-5 hours implementation)
- [ ] **Portfolio Health Dashboard**
  - [ ] Overall portfolio performance vs. benchmarks
  - [ ] Sector allocation breakdown
  - [ ] Geographic exposure (CAD vs USD)
  - [ ] Liquidity analysis (days to liquidate)

- [ ] **Enhanced Daily P&L Features**
  - [ ] Real-time price updates during market hours (use currentPrice from yfinance)
  - [ ] After-hours price movement inclusion in daily P&L
  - [ ] Market status indicator (Open/Closed/Pre-Market/After Hours)
  - [ ] Timezone handling for US vs Canadian market hours
  - [ ] Pre-market price integration for early morning calculations

- [ ] **Enhanced Instructions**
  - [ ] Add position-specific trading recommendations
  - [ ] Include stop-loss analysis and suggestions
  - [ ] Add position sizing guidance
  - [ ] Include market regime context

### 📊 **Future Enhancements** (When portfolio grows)
- [ ] **Advanced Analytics**
  - [ ] Sharpe ratio and risk-adjusted returns
  - [ ] Correlation analysis between positions
  - [ ] VaR calculations
  - [ ] Stress testing scenarios

- [ ] **Market Intelligence**
  - [ ] News sentiment integration
  - [ ] Analyst coverage updates
  - [ ] Earnings calendar integration
  - [ ] Options flow data

## 🚀 **Implementation Plan**

### Phase 1: Quick Wins (This Week)
1. ✅ **Daily P&L Calculation** - Fixed N/A issue, implemented industry standards
2. **Enhanced Position Display** - Show P&L, weights, performance
3. **Basic Risk Metrics** - Concentration, volatility, drawdown
4. **Improved Market Data** - Multi-timeframe, volume trends

### Phase 2: Portfolio Health (Next Week)
1. **Portfolio Dashboard** - Overall health metrics
2. **Enhanced Instructions** - Position-specific guidance

### Phase 3: Advanced Features (When Needed)
1. **Advanced Analytics** - When portfolio has 10+ positions
2. **Market Intelligence** - When complexity requires it

## 📝 **Notes**
- Focus on features that help with 3-position portfolio management
- Prioritize clarity and actionable information
- Keep implementation simple and maintainable
- Test each enhancement with real data before moving to next phase

## 🎯 **Success Metrics**
- LLM can quickly assess portfolio health
- Clear understanding of position performance
- Better risk awareness for small portfolio
- Actionable insights for trading decisions
