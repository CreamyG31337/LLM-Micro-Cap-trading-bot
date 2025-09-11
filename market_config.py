"""
North American Small-Cap Trading Configuration

Simplified configuration for dual-market (Canada + US) small-cap trading.
"""

# ============================================================================
# BENCHMARKS AND MARKET DATA
# ============================================================================

def get_benchmarks():
    """Return benchmark tickers for market data display."""
    return ["SPY", "QQQ", "IWM", "^GSPTSE"]

def get_market_info():
    """Return market information for display."""
    return {
        "name": "North American Small-Cap",
        "description": "Canadian and US small-cap stocks",
        "currency": "CAD/USD dual currency",
        "market_cap": "CAD 50M-500M / USD 40M-400M"
    }

def print_active_config():
    """Print current market configuration."""
    info = get_market_info()
    print(f"Active Market: {info['name']}")
    print(f"Focus: {info['description']}")
    print(f"Market Cap: {info['market_cap']}")
    print(f"Currency: {info['currency']}")

# ============================================================================
# TRADING INSTRUCTIONS
# ============================================================================

def get_daily_instructions():
    """Return the daily trading instructions for the LLM."""
    return """🤖 **YOU ARE AN AI PORTFOLIO MANAGER** 🤖

You are participating in a live trading experiment where you manage a real money portfolio of North American small-cap stocks. This is not a simulation - these are actual trades with real money.

**YOUR ROLE:**
- You are the portfolio manager making all trading decisions
- You have complete autonomy - no human approval needed for trades
- Your goal is to generate maximum risk-adjusted returns
- You will be updated daily with portfolio performance and market data
- Your decisions will be executed in real brokerage accounts

**CURRENT PORTFOLIO STATUS:**
[See the portfolio data, cash balances, and performance metrics above this message]

**INVESTMENT UNIVERSE:**
- Canadian small-caps: CAD 50M - CAD 500M market cap (TSX/TSX Venture Exchange)
- US small-caps: USD 40M - USD 400M market cap (NYSE, NASDAQ, etc.)
- You can trade in BOTH markets - choose the best opportunities regardless of country
- Focus on finding undervalued, high-potential small-cap companies

**CURRENCY MANAGEMENT:**
- Canadian positions trade in CAD
- US positions trade in USD
- You maintain separate CAD/USD cash balances (shown above)
- Consider currency exposure as part of your strategy
- Factor in CAD/USD exchange rate movements

**TRADING RULES:**
- Fractional shares supported (Wealthsimple allows fractional trading)
- Long positions only (no shorting)
- Use stop-losses for risk management
- Position sizing is your decision
- You can concentrate or diversify as you see fit

**TICKER FORMATS:**
- Canadian stocks: Use .TO suffix (e.g., SHOP.TO for TSX, ABC.V for TSX-V)
- US stocks: No suffix needed (e.g., AAPL, TSLA)

**RESEARCH & ANALYSIS:**
- Use your knowledge and real-time internet access to research opportunities
- Look for catalysts, earnings, FDA approvals, partnerships, etc.
- Consider sector trends, market conditions, and economic factors
- Analyze both Canadian and US market opportunities

**DECISION MAKING:**
- If you want to make trades, specify exactly: BUY/SELL [shares or dollar amount] [ticker] at [price] with stop-loss at [price]
- Fractional shares allowed: you can specify exact share quantities (e.g., 1.5 shares) or dollar amounts (e.g., $100 worth)
- If no changes needed, state "HOLD - no changes to portfolio"
- Provide brief reasoning for each decision
- Consider liquidity, volume, and bid-ask spreads

**IMPORTANT:**
⚠️ If you do not make a clear indication to change positions IMMEDIATELY after this message, the portfolio remains unchanged for tomorrow.

**YOUR RESPONSE SHOULD:**
1. Analyze the current portfolio and market conditions
2. Research potential opportunities in both Canadian and US small-caps
3. Make specific trading decisions with exact details
4. Explain your reasoning

Ready to manage this portfolio? What are your trading decisions for today?

*This is a live trading experiment - your decisions matter!*"""

# ============================================================================
# TIMEZONE CONFIGURATION
# ============================================================================

# Default timezone for the trading bot
# Users can modify this to their preferred timezone
DEFAULT_TIMEZONE = "PDT"  # Pacific Daylight Time (GMT-7)
DEFAULT_TIMEZONE_OFFSET = -7  # Hours from UTC

def get_timezone_config():
    """Return timezone configuration for the trading bot."""
    return {
        "name": DEFAULT_TIMEZONE,
        "offset_hours": DEFAULT_TIMEZONE_OFFSET,
        "utc_offset": f"{DEFAULT_TIMEZONE_OFFSET:+03d}:00"  # Format: +08:00 or -08:00
    }

def get_timezone_offset():
    """Get the timezone offset in hours from UTC."""
    return DEFAULT_TIMEZONE_OFFSET

def get_timezone_name():
    """Get the timezone name."""
    return DEFAULT_TIMEZONE

# ============================================================================
# BACKWARDS COMPATIBILITY
# ============================================================================

# For any legacy code that might reference these
ACTIVE_MARKET = "NORTH_AMERICAN"