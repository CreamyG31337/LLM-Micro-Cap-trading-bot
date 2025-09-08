# North American Small-Cap Trading Guide

## 🌎 **Best of Both Worlds: US + Canadian Small Caps**

Your system is now configured for **North American small-cap trading** - giving your AI access to opportunities in both Canadian and US markets simultaneously.

## 🎯 **Current Configuration**

**Market Universe:**
- **Canadian Small-Caps**: CAD 50M - CAD 500M market cap (TSX/TSX Venture)
- **US Small-Caps**: USD 40M - USD 400M market cap (NYSE, NASDAQ, etc.)
- **AI Decides**: Let the AI choose the best opportunities regardless of country

**Currency Management:**
- Canadian positions: Trade in CAD
- US positions: Trade in USD
- Maintain separate CAD/USD balances (as supported by your broker)

## 🚀 **How It Works**

### **Daily Trading Process:**
1. **Run the script:**
   ```bash
   python trading_script.py --file "my trading/llm_portfolio_update.csv"
   ```

2. **System provides North American context:**
   - Benchmarks from both markets (SPY, QQQ, IWM, TSX Composite)
   - Instructions covering both US and Canadian opportunities
   - Guidance on currency management and ticker formats

3. **LLM gets comprehensive instructions:**
   - Can recommend Canadian stocks (SHOP.TO, ABC.V format)
   - Can recommend US stocks (AAPL, TSLA format)
   - Considers currency exposure and exchange rates
   - Factors in different market dynamics

## 💰 **Currency & Cash Management**

### **Broker Support:**
- **WealthSimple**: Supports both CAD and USD trading
- **Webull**: Multi-currency trading available
- **Most Canadian brokers**: Handle currency conversion automatically

### **AI Guidance:**
The system instructs your AI to:
- Consider currency exposure in position sizing
- Account for CAD/USD exchange rate impacts
- Balance between CAD and USD positions
- Factor in currency hedging if desired

### **Cash Balance Tracking:**
You can track cash as:
1. **Single balance** (broker handles conversion)
2. **Separate CAD/USD balances** (more precise tracking)
3. **Combined CAD-equivalent** (simplified reporting)

## 📊 **Market Comparison Features**

### **Benchmarks Include:**
- **SPY**: S&P 500 (US large-cap baseline)
- **QQQ**: NASDAQ 100 (US tech focus)
- **IWM**: Russell 2000 (US small-cap comparison)
- **^GSPTSE**: TSX Composite (Canadian market baseline)

### **Performance Tracking:**
- Compare your portfolio against both US and Canadian indices
- See how your picks perform vs. traditional small-cap benchmarks
- Track currency impact on returns

## 🎯 **AI Decision Framework**

Your LLM now receives instructions to consider:

### **Opportunity Assessment:**
- **Canadian advantages**: Resource sector, healthcare innovation, cannabis
- **US advantages**: Larger market, higher liquidity, tech ecosystem
- **Cross-market arbitrage**: Similar companies trading at different valuations

### **Risk Management:**
- **Currency risk**: CAD/USD exposure
- **Regulatory differences**: CSA vs SEC rules
- **Market hours**: TSX (9:30 AM - 4:00 PM ET) vs US markets
- **Liquidity differences**: US generally higher volume

### **Sector Considerations:**
- **Canadian strengths**: Mining, energy, biotech, cannabis
- **US strengths**: Technology, consumer goods, financial services
- **Overlap opportunities**: Cross-listed companies, similar sectors

## 🔄 **Quick Market Switching**

You can still switch to single-market focus anytime:

```bash
# Both markets (current setup)
python switch_market.py north_american

# Canadian only
python switch_market.py canadian

# US only  
python switch_market.py us

# Check current setting
python switch_market.py status
```

## 📝 **Example LLM Interactions**

### **Sample AI Response (North American Mode):**
```
Based on current market conditions, I recommend:

1. BUY 50.5 shares of XYZ.TO (Canadian biotech, CAD $4.50) - fractional shares supported
   - Reason: Phase 2 trial results due next month
   - Stop-loss: CAD $3.60

2. BUY 75.25 shares of ABCD (US tech micro-cap, USD $12.30) - fractional shares supported  
   - Reason: Strong Q3 earnings, expanding market share
   - Stop-loss: USD $10.00

Currency allocation: ~60% CAD exposure, 40% USD exposure
```

### **Ticker Format Recognition:**
- **Canadian**: SHOP.TO, RBC.TO, ABC.V, DEF.V
- **US**: AAPL, TSLA, MSFT (no suffix)
- **AI automatically knows** which exchange based on format

## 🛠 **Advanced Features**

### **Portfolio Analytics:**
- Track CAD vs USD position allocation
- Monitor currency exposure impact
- Compare Canadian vs US position performance
- Analyze sector distribution across both markets

### **Risk Management:**
- Set maximum currency exposure limits
- Balance between market exposures
- Consider correlation between Canadian and US small-caps
- Factor in commodity price impacts (affects both markets differently)

## 💡 **Strategy Benefits**

### **Diversification:**
- **Geographic**: Reduce single-country risk
- **Regulatory**: Different regulatory environments
- **Sector**: Access to unique Canadian sectors (resources, cannabis)
- **Currency**: Natural hedge between CAD and USD

### **Opportunity Expansion:**
- **Larger universe**: ~2x more stocks to choose from
- **Market inefficiencies**: Exploit valuation differences
- **Sector specialists**: Canadian resource expertise + US tech innovation
- **Liquidity options**: Choose most liquid opportunities

### **Risk Mitigation:**
- **Market correlation**: Canadian and US small-caps aren't perfectly correlated
- **Economic cycles**: Different economic drivers
- **Currency buffer**: CAD/USD movements can offset market moves
- **Regulatory diversity**: Spread regulatory risk

## 🚨 **Important Considerations**

### **Tax Implications:**
- **Withholding taxes**: US stocks may have withholding tax for Canadian residents
- **Currency gains/losses**: May be taxable events
- **Consult tax professional**: For specific Canadian tax treatment

### **Trading Costs:**
- **Currency conversion**: Some brokers charge conversion fees
- **Cross-border fees**: May apply to US stock trades
- **Compare brokers**: WealthSimple vs Webull vs others for total costs

### **Market Hours:**
- **TSX**: 9:30 AM - 4:00 PM ET
- **US Markets**: 9:30 AM - 4:00 PM ET (same hours!)
- **Pre/post market**: Different availability between markets

## 🎉 **Getting Started**

1. **Verify current setup:**
   ```bash
   python switch_market.py status
   ```

2. **Should show:**
   ```
   Active Market: NORTH_AMERICAN
   Currency: CAD/USD
   Market Cap Range: CAD 50M - CAD 500M or USD 40M - USD 400M
   Exchanges: TSX/TSXV/US Exchanges
   ```

3. **Start trading:**
   ```bash
   python trading_script.py --file "my trading/llm_portfolio_update.csv"
   ```

4. **Let the AI decide** between Canadian and US opportunities!

## 🌟 **Why This Approach Rocks**

- **Maximum flexibility**: AI chooses best opportunities regardless of country
- **Natural diversification**: Geographic and currency spread
- **Larger opportunity set**: Access to both markets' small-cap gems
- **Real-world practical**: Matches how modern Canadian investors actually trade
- **Currency management**: Built into the AI's decision framework

Perfect setup for a Canadian investor with access to both markets! 🇨🇦🇺🇸📈
