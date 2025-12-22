# Performance Tracking & Fund Metrics Explained

This document explains the core concepts used in the dashboard to track performance, calculate returns, and ensure fair withdrawals for all investors.

---

## 1. The Two Ways We Track Performance

We use **two different metrics** to track performance, each serving a specific purpose:

### A. Cost Basis Return → **Graph (Stock Performance)**
*   **What it measures:** How well our stock picks are performing
*   **Formula:** `(Current Market Value - Cost Basis) / Cost Basis`
*   **Example:** Buy stocks for $10,000 → Now worth $11,873 → **+18.7% return**
*   **Best for:** Comparing our trading strategy to benchmarks (S&P 500, NASDAQ, etc.)
*   **Important:** This ignores uninvested cash. If we have $2k sitting in cash and $10k in stocks that went up 18%, the graph shows +18% (the stocks' performance), not the blended return.

### B. NAV Return → **Your Wallet (Personal Return)**
*   **What it measures:** How much YOUR specific investment has grown
*   **Formula:** `(Current NAV - Entry NAV) / Entry NAV`
*   **Example:** You bought in when NAV was $1.03 → Now NAV is $0.87 → **-15.5% return**
*   **Best for:** Determining how much you can withdraw and ensuring fairness
*   **Critical difference:** This accounts for WHEN you entered the fund, not just how the stocks performed

---

## 2. Why NAV is Critical for Fair Withdrawals

### The Problem Without NAV

Imagine this scenario:
1.  **Jan 1:** You invest **$100**. Fund buys Stock A.
2.  **Feb 1:** Stock A doubles. Your $100 is now worth **$200**.
3.  **Feb 2:** Your friend invests **$1,000** in cash.

**Question:** If the fund is worth $1,200 total ($200 stocks + $1,000 cash), do you each own 50%?

**Answer:** **NO!** You turned $100 into $200. Your friend just deposited $1,000. You deserve 100% of the gain.

---

### The Solution: NAV Units (Like Mutual Funds)

**How NAV Works:**

| Date | Event | Portfolio Value | Total Units | NAV | Your Units | Friend's Units |
|------|-------|----------------|-------------|-----|-----------|---------------|
| **Jan 1** | You invest $100 | $100 | 100 | **$1.00** | 100 | 0 |
| **Feb 1** | Stock doubles | $200 | 100 | **$2.00** | 100 | 0 |
| **Feb 2** | Friend invests $1,000 | $1,200 | 600 | **$2.00** | 100 | 500 |

**Breakdown:**
- **Your 100 units** × $2.00 NAV = **$200** (100% return on your $100)
- **Friend's 500 units** × $2.00 NAV = **$1,000** (0% return, just got here)

**When you withdraw:** You redeem your 100 units at the current NAV. If NAV is $2.50, you get $250. Fair!

---

## 3. Dashboard Metrics Reference

| Metric | What It Shows | Location | Who Sees It |
|--------|---------------|----------|-------------|
| **Performance Graph** | Stock picking skill vs benchmarks | Main Chart | Everyone |
| **Your Return %** | Your personal investment growth | Sidebar | Individual |
| **Your Ownership %** | Your slice of the total fund | Sidebar | Individual |
| **Fund Return %** | Overall fund health (including cash) | Header | Everyone |
| **Investor Allocations** | Who owns what % of the fund | Pie Chart | Admin only |

---

## 4. Real Example: Why Your Return ≠ Fund Return

**Current Fund Status (Dec 2024):**
- Total Contributions: $11,525
- Current Portfolio Value: $11,344
- **Overall Fund Return:** -1.6% (includes $2k uninvested cash)
- **Stock Performance:** +18.7% (the graph shows this)

**Your Personal Situation:**
- You contributed: $6,380
- Your current value: $6,167
- **Your Return:** -3.3%

**Why the difference?**
- You entered the fund when NAV was higher (~$1.03)
- Current NAV is lower (~$0.87)
- Even though the stocks picked AFTER you joined did great (+18.7%), the ones you bought into have underperformed
- This is FAIR - you're not penalized for timing, but you're also not credited for gains that happened before you invested

---

## 5. The "Same-Day Contribution" Bug (Fixed Dec 2024)

### What Was Wrong

**Before the fix**, if multiple people contributed on the same day:

| Time | Event | Units Calculated | Problem |
|------|-------|-----------------|---------|
| 9:00 AM | Person A deposits $1,000 | NAV = $1.00, gets 1,000 units | ✅ Correct |
| 11:00 AM | Person B deposits $1,000 | NAV = $1.00 (portfolio value / 1,000 units) = $1.00, gets 1,000 units | ✅ Correct |
| 2:00 PM | Person C deposits $1,000 | NAV calc used 2,000 units (A+B), not the start-of-day units! | ❌ **WRONG** |

Person C would get FEWER units because the math was using the growing unit count instead of the START of day units.

### How We Fixed It

**Now:** We "freeze" the unit count at the start of each trading day. Everyone buying in on Sept 8th uses the SAME denominator (units at market open on Sept 8th), regardless of what time their contribution arrived.

**Code:**
```python
if date_str != last_contribution_date:
    units_at_start_of_day = total_units  # Snapshot at start of new day
    last_contribution_date = date_str

# Later...
nav = portfolio_value / units_at_start_of_day  # Use snapshot, not current total
```

---

## 6. Common Questions

### Q: Why does the graph show +18% but I'm down -3%?
**A:** The graph shows how well the STOCKS perform. Your return shows how well YOUR INVESTMENT performed based on when you bought in. If you entered when NAV was high and it dropped, you're down even if the stocks picked afterward did great.

### Q: Can I withdraw based on the graph performance (+18%)?
**A:** No. Withdrawals are based on YOUR units × CURRENT NAV. This ensures fairness - you can't claim returns from before you invested.

### Q: What if I contributed on a weekend?
**A:** The system looks back up to 7 days to find the most recent trading day's NAV and uses that price.

### Q: Does uninvested cash hurt my return?
**A:** For YOUR return (NAV-based), yes - cash sitting uninvested dilutes the fund's growth. For the GRAPH (stock performance), no - it only tracks the stocks that were actually purchased.

### Q: How do I know my numbers are correct?
**A:** Check the logs (Admin page) for any "NAV FALLBACK" warnings. If you see those, it means the system had to estimate NAV for some contributions due to missing data.

---

## 7. Technical Details

### NAV Calculation Process

1. **Portfolio Snapshot:** At market close (4 PM ET), we record the total value of all positions
2. **Unit Calculation:** For each contribution, we calculate `units = amount / NAV_at_contribution_time`
3. **Your Value:** `your_units × current_NAV`
4. **Your Return:** `(current_NAV / entry_NAV) - 1`

### Edge Cases Handled

- ✅ First contribution (NAV starts at $1.00)
- ✅ Same-day multiple contributions (use start-of-day NAV)
- ✅ Weekend/holiday contributions (7-day lookback)
- ✅ Missing historical data (time-weighted estimation)
- ✅ Withdrawals (redeem at current NAV)
- ✅ Division by zero (fallback to NAV = 1.0)

---

## 8. For Developers: Files to Check

- **Primary Logic:** `web_dashboard/streamlit_utils.py`
  - `get_user_investment_metrics()` - Your sidebar numbers
  - `get_investor_allocations()` - Pie chart ownership
  - `calculate_portfolio_value_over_time()` - Graph data
  
- **Historical Data:** `portfolio_positions` table (Supabase)
- **Contributions:** `fund_contributions` table (Supabase)
