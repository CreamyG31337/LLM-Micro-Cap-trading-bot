# Graph Normalization Logic Documentation

## Overview
The portfolio performance graph uses a sophisticated normalization system to ensure fair comparison between your fund and benchmark indices. This document explains the complete logic and rationale.

## Key Components

### 1. Portfolio Data Timeline
- **Baseline Day**: One day before the first actual trading data (e.g., 2025-08-24)
  - Portfolio value: $0 (no positions yet)
  - Purpose: Provides a common starting point for comparison
- **First Trading Day**: First day with actual portfolio data (e.g., 2025-08-25)
  - Portfolio value: Actual invested amount (e.g., $76,205.76)
  - Purpose: Shows real performance from first investment

### 2. Benchmark Normalization
- **Baseline Date**: Uses the first actual trading day (not the baseline day)
- **Normalization**: Benchmarks are normalized to start at exactly $100
- **Rationale**: Ensures fair comparison by starting both portfolio and benchmarks from the same reference point

### 3. Performance Index Calculation
```python
# Portfolio Performance Index
llm_totals["Performance_Index"] = llm_totals["Performance_Pct"] + 100

# Benchmark Performance Index  
scaling_factor = 100.0 / baseline_close
benchmark_data[column_name] = benchmark_data["Close"] * scaling_factor
```

## Timeline Example

```
Date        Portfolio Value    Portfolio Index    Benchmark Index
2025-08-24  $0.00 (baseline)  100.00 (baseline)  N/A (weekend)
2025-08-25  $75,865.76       99.55 (-0.45%)     100.00 (baseline)
2025-08-26  $89,086.77       99.74 (-0.26%)     100.15 (+0.15%)
...
2025-09-22  $230,003.07      106.17 (+6.17%)     105.50 (+5.50%)
```

## Key Benefits

### 1. Fair Comparison
- Both portfolio and benchmarks start from the same baseline
- Eliminates "down a bit" start that was confusing
- Shows relative performance clearly

### 2. Realistic Performance
- Portfolio shows actual performance from first investment
- Benchmarks show market performance over the same period
- Easy to see which performed better

### 3. Clean Visualization
- All lines start from the same point
- Performance differences are immediately visible
- No artificial normalization that distorts reality

## Implementation Details

### Portfolio Data Processing
```python
# Add baseline day one day before first data
baseline_date = earliest_date - pd.Timedelta(days=1)
all_dates = pd.concat([pd.Series([baseline_date]), pd.Series(all_dates)]).sort_values()

# Handle baseline day (no portfolio data yet)
if len(daily_snapshots) == 0:
    daily_snapshots.append({
        "Date": current_date,
        "Cost_Basis": 0.0,
        "Market_Value": 0.0,
        "Unrealized_PnL": 0.0,
        "Performance_Pct": 0.0
    })
```

### Benchmark Normalization
```python
# Use first actual trading day for benchmark baseline
first_trading_day = llm_totals[llm_totals["Cost_Basis"] > 0]["Date"].min()
benchmark_start_date = first_trading_day

# Normalize benchmark to $100 baseline
baseline_close = benchmark_data_on_start_date
scaling_factor = 100.0 / baseline_close
benchmark_data[column_name] = benchmark_data["Close"] * scaling_factor
```

## Edge Cases Handled

### 1. Weekend/Holiday Baselines
- If baseline day is weekend/holiday, benchmarks use closest trading day
- Portfolio baseline day is always included for consistency

### 2. Missing Data
- If no benchmark data available, creates flat $100 baseline
- If no portfolio data, creates $0 baseline entry

### 3. Date Alignment
- Portfolio and benchmark dates are aligned using forward-fill for weekends
- Ensures continuous timeline for proper comparison

## Performance Metrics

### Portfolio Metrics
- **Peak Performance**: Highest percentage gain achieved
- **Max Drawdown**: Largest percentage loss from peak
- **Total Return**: Overall performance from baseline to current

### Benchmark Metrics
- **Relative Performance**: Portfolio vs benchmark performance
- **Outperformance**: How much better/worse than benchmark
- **Risk-Adjusted Returns**: Performance per unit of risk

## Troubleshooting

### Common Issues
1. **Benchmarks starting below $100**: Fixed by using first actual trading day for normalization
2. **Portfolio starting "down a bit"**: Fixed by adding baseline day before first data
3. **Inconsistent timelines**: Fixed by proper date alignment and forward-fill

### Validation
- Portfolio and benchmarks should start at same baseline
- Performance percentages should be realistic
- Timeline should be continuous with no gaps

## Future Improvements

### Potential Enhancements
1. **Risk Metrics**: Add Sharpe ratio, volatility comparison
2. **Sector Analysis**: Break down performance by sector
3. **Interactive Charts**: Add zoom, hover details
4. **Export Options**: PDF, PNG, CSV data export

### Configuration Options
1. **Baseline Period**: Allow custom baseline period selection
2. **Benchmark Selection**: Easy switching between different benchmarks
3. **Time Range**: Custom start/end date selection
4. **Display Options**: Show/hide different metrics

## Conclusion

The graph normalization system provides a fair, accurate, and intuitive way to compare portfolio performance against market benchmarks. The key insight is using a common baseline day while ensuring benchmarks start at exactly $100 for easy comparison.
