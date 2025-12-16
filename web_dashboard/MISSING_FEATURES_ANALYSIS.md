# Web Dashboard Missing Features Analysis

## Overview
This document compares the console application features with the web dashboard to identify missing functionality.

**Last Updated:** 2025-01-27

---

## Console App Features vs Web Dashboard

### ✅ **Currently Available in Web Dashboard**

1. **Portfolio Dashboard** - Basic portfolio view with charts
2. **Admin Features:**
   - Scheduled Tasks Management
   - User Management (assign funds, delete users)
   - Contributor Access Management
   - Fund Management (create, rename, delete, wipe)
   - System Status Monitoring
   - Trade Entry (basic buy/sell)
   - Contribution Management
   - Application Logs

---

## ❌ **Missing Features from Web Dashboard**

### **1. Trade Management & History**

#### **View Trade Log** (Console: `'l'` or menu option)
- **Console**: Formatted table view of complete trade history
- **Missing**: Detailed trade log viewer with:
  - Sortable columns
  - Filter by ticker, date range, fund
  - Export to CSV
  - Trade details (reason, P&L, currency)
- **Priority**: High
- **Database**: `trade_log` table exists

#### **Add Trade from Email** (Console: `'e'`)
- **Console**: Parse email notifications and add trades automatically
- **Missing**: Email parsing interface or manual trade import
- **Priority**: Medium
- **Note**: May require email integration setup

---

### **2. Cash & Contribution Management**

#### **Update Cash Balances** (Console: `'u'`)
- **Console**: Interactive cash balance update (CAD/USD)
- **Missing**: 
  - Cash balance update interface
  - View current cash balances
  - History of cash balance changes
- **Priority**: High
- **Database**: `cash_balances` table exists

#### **Sync Fund Contributions** (Console: `'sync'`)
- **Console**: Sync contributions between CSV and database
- **Missing**: Contribution sync tool
- **Priority**: Medium
- **Note**: May be less relevant if using Supabase only

---

### **3. Portfolio Operations**

#### **Rebuild Portfolio** (Console: `'r'` or `'rebuild'`)
- **Console**: Rebuild portfolio from trade log (fixes display issues)
- **Missing**: 
  - Portfolio rebuild tool
  - Force refresh from trade log
  - Data integrity checker
- **Priority**: High
- **Use Case**: Fixes duplicate entries, recalculates positions

#### **Sort Portfolio** (Console: `'o'`)
- **Console**: Sort portfolio by various criteria
- **Missing**: 
  - Sort options in portfolio view
  - Sort by: P&L, value, ticker, date opened, etc.
- **Priority**: Medium
- **Note**: Can be added to existing portfolio view

---

### **4. Prompt Generation & LLM Integration**

#### **Generate Daily Trading Prompt** (Console: `'d'`)
- **Console**: Generate daily trading prompt with current portfolio data
- **Missing**: 
  - Daily prompt generator
  - Export prompt to clipboard/file
  - Include market context, portfolio status
- **Priority**: Medium
- **Use Case**: For LLM-assisted trading decisions

#### **Generate Weekly Deep Research Prompt** (Console: `'w'`)
- **Console**: Comprehensive weekly research prompt
- **Missing**: 
  - Weekly deep research prompt generator
  - More detailed analysis than daily
- **Priority**: Low
- **Use Case**: Weekly portfolio review

#### **Show Prompt** (Console: `'9'`)
- **Console**: Display current LLM prompt template
- **Missing**: 
  - View prompt templates
  - Edit prompt templates (admin)
- **Priority**: Low

#### **Simple Automation** (Console: `'2'`)
- **Console**: LLM-powered automated trading (requires OpenAI API key)
- **Missing**: 
  - LLM integration for automated trading
  - API key management
  - Automated trade execution
- **Priority**: Low
- **Note**: May require significant security considerations

---

### **5. Graph & Performance Analysis**

#### **Generate Performance Graph** (Console: `'3'`)
- **Console**: Create performance comparison charts from trading data
- **Missing**: 
  - Performance graph generator
  - Export charts
  - Historical performance visualization
- **Priority**: Medium
- **Note**: Dashboard has some charts, but not the same generation tool

#### **Graph Benchmarks (365 days)** (Console: `'4'`)
- **Console**: Generate benchmark performance graphs (S&P 500, QQQ, Russell 2000, VTI)
- **Missing**: 
  - Benchmark comparison charts
  - 365-day performance graphs
  - Multiple benchmark overlays
- **Priority**: Medium
- **Note**: Dashboard has some benchmark comparison, but not the same tool

---

### **6. Contributor Management**

#### **Manage Contributors** (Console: `'m'`)
- **Console**: Edit contributor names and email addresses interactively
- **Missing**: 
  - Contributor editing interface (beyond basic admin)
  - Bulk contributor updates
  - Contributor merge/deduplication
- **Priority**: Medium
- **Note**: Admin has contributor access management, but not the same editing tool

#### **Get Contributor Emails** (Console: `'x'`)
- **Console**: Output all contributor email addresses (semicolon-separated)
- **Missing**: 
  - Export contributor emails
  - Copy to clipboard
  - Email list generation
- **Priority**: Low

---

### **7. System Management**

#### **Backup & Cache Management** (Console: `'k'` or `'cache'`)
- **Console**: Comprehensive cache and backup management
- **Missing**: 
  - Cache management interface:
    - Price cache
    - Fundamentals cache
    - Exchange rate cache
    - Memory caches
  - Cache statistics
  - Clear cache options
- **Priority**: High
- **Use Case**: Performance optimization, troubleshooting

#### **Create Backup** (Console: `'backup'`)
- **Console**: Create data backup
- **Missing**: 
  - Manual backup creation
  - Backup scheduling
  - Backup download
- **Priority**: Medium

#### **Restore from Backup** (Console: `'restore'`)
- **Console**: Restore from backup
- **Missing**: 
  - Backup restore interface
  - Backup selection
  - Restore confirmation
- **Priority**: Medium
- **Note**: Requires careful security considerations

#### **Backup Statistics** (Console: `'0'`)
- **Console**: View backup statistics
- **Missing**: 
  - Backup size, count
  - Backup history
  - Storage usage
- **Priority**: Low

#### **Clean Old Backups** (Console: `'9'`)
- **Console**: Clean old backup files
- **Missing**: 
  - Backup cleanup tool
  - Retention policy management
- **Priority**: Low

---

### **8. Configuration & Settings**

#### **Configure** (Console: `'c'`)
- **Console**: Configuration options and setup
- **Missing**: 
  - System configuration interface
  - Settings management
  - Repository configuration
- **Priority**: Medium
- **Note**: Some settings may be admin-only

#### **Switch Repository** (Console: `'d'`)
- **Console**: Switch between CSV and Supabase repositories
- **Missing**: 
  - Repository switching interface
  - Repository status display
  - Test repository connection
- **Priority**: Low
- **Note**: May be less relevant for web-only deployment

#### **Switch Fund** (Console: `'f'`)
- **Console**: Quickly switch between available funds
- **Missing**: 
  - Fund switcher in dashboard
  - Quick fund selection
- **Priority**: Medium
- **Note**: Dashboard has fund filter, but not quick switcher

---

### **9. Debug & Development Tools**

#### **Debug Instructions** (Console: `'8'`)
- **Console**: Show debug information and instructions
- **Missing**: 
  - Debug information page
  - Troubleshooting guide
  - System diagnostics
- **Priority**: Low
- **Note**: Admin has system status, but not debug instructions

#### **Clear Test Data** (Console: `'z'`)
- **Console**: Clear all data for test funds
- **Missing**: 
  - Test data cleanup tool
  - Selective data clearing
- **Priority**: Low
- **Note**: Admin has fund wipe, but not test-specific

---

## 📊 **Priority Summary**

### **High Priority** (Core Functionality)
1. ✅ **View Trade Log** - Essential for trade history
2. ✅ **Update Cash Balances** - Core portfolio management
3. ✅ **Rebuild Portfolio** - Data integrity tool
4. ✅ **Cache Management** - Performance and troubleshooting

### **Medium Priority** (Important Features)
1. **Sort Portfolio** - User experience improvement
2. **Generate Performance Graph** - Analysis tool
3. **Graph Benchmarks** - Performance comparison
4. **Generate Daily Trading Prompt** - LLM integration
5. **Manage Contributors** - Enhanced contributor editing
6. **Backup Management** - Data safety
7. **Configuration Interface** - System setup

### **Low Priority** (Nice to Have)
1. **Weekly Deep Research Prompt** - Advanced feature
2. **Get Contributor Emails** - Utility feature
3. **Show Prompt** - Template viewing
4. **Simple Automation** - Advanced LLM feature
5. **Add Trade from Email** - Automation feature
6. **Switch Repository** - May not be needed for web
7. **Debug Instructions** - Development tool

---

## 🗄️ **Database Schema Coverage**

### **Tables Used by Console but Not Fully Exposed in Web:**

1. **`trade_log`** ✅ Exists - Used for trade entry, but missing detailed viewer
2. **`cash_balances`** ✅ Exists - Missing update interface
3. **`performance_metrics`** ✅ Exists - Used but missing generation tools
4. **`securities`** ✅ Exists - Used for ticker validation
5. **`exchange_rates`** ✅ Exists - Used by scheduler, missing manual update
6. **`fund_contributions`** ✅ Exists - Used in admin, missing sync tool

### **Additional Tables/Views Available:**
- `contributor_ownership` (view) - Used in admin
- `fund_contributor_summary` (view) - May not be exposed
- `current_positions` (view) - Used in dashboard

---

## 🎯 **Recommended Implementation Order**

### **Phase 1: Core Missing Features**
1. Trade Log Viewer (detailed, sortable, filterable)
2. Cash Balance Update Interface
3. Portfolio Rebuild Tool
4. Cache Management Interface

### **Phase 2: Enhanced Functionality**
1. Sort Portfolio Options
2. Performance Graph Generator
3. Benchmark Graphing Tool
4. Daily Prompt Generator

### **Phase 3: Advanced Features**
1. Backup Management
2. Configuration Interface
3. Enhanced Contributor Management
4. Email Trade Import

---

## 📝 **Notes**

- Some features may require additional database views or functions
- Security considerations for backup/restore and automation features
- Some console features may not translate directly to web (e.g., email parsing)
- Consider user permissions for different features (admin vs regular user)
- Some features may require API integrations (e.g., OpenAI for automation)

