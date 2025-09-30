# 🔍 Shared Data Access System

## Overview
This system provides both visual and programmatic access to trading data for both developers and LLMs. It allows debugging, analysis, and monitoring of the trading bot's database.

## 🎯 Goals
- **Developer Access**: Visual dashboard for debugging and monitoring
- **LLM Access**: API endpoints for programmatic data analysis
- **Shared Understanding**: Both can see the same data and debug together
- **Easy Debugging**: SQL interface for complex queries

## 🏗️ Architecture

```
Trading Bot → Supabase Database → Web Dashboard
                    ↓
            ┌─────────────────┐
            │  Shared Access  │
            └─────────────────┘
                    ↓
        ┌─────────────────────────┐
        │  Developer Dashboard    │  ← Visual interface
        │  SQL Interface         │  ← Query debugging
        │  Data Export APIs      │  ← LLM access
        └─────────────────────────┘
```

## 📊 Components

### 1. SQL Interface (`/dev/sql`)
- **Purpose**: Execute SQL queries directly on the database
- **Access**: Admin only
- **Features**:
  - Query editor with syntax highlighting
  - Safe query execution (read-only by default)
  - Results display in table format
  - Query history

### 2. Data Export APIs (`/api/export/*`)
- **Purpose**: Provide structured data for LLM analysis
- **Access**: Admin only
- **Endpoints**:
  - `/api/export/portfolio` - Portfolio positions
  - `/api/export/trades` - Trade history
  - `/api/export/performance` - Performance metrics
  - `/api/export/cash` - Cash balances

### 3. Developer Dashboard (`/dev/dashboard`)
- **Purpose**: Visual overview of key metrics
- **Access**: Admin only
- **Features**:
  - Portfolio summary
  - Recent trades
  - Performance charts
  - Quick metrics

## 🔧 Implementation Status

### ✅ Completed
- [x] Project structure analysis
- [x] Requirements definition
- [x] Architecture design

### 🚧 In Progress
- [ ] SQL interface implementation
- [ ] Data export API endpoints
- [ ] Developer dashboard
- [ ] Testing and validation

### 📋 Pending
- [ ] Documentation for API endpoints
- [ ] Security considerations
- [ ] Performance optimization
- [ ] Error handling

## 🚀 Usage

### For Developers
1. **Visual Dashboard**: Visit `/dev/dashboard`
2. **SQL Queries**: Visit `/dev/sql`
3. **Data Export**: Use API endpoints

### For LLMs
1. **API Access**: Call `/api/export/*` endpoints
2. **Data Analysis**: Process JSON responses
3. **Debugging**: Query specific data points

## 🔒 Security
- All endpoints require admin authentication
- SQL queries are sandboxed (read-only by default)
- Rate limiting on API endpoints
- Input validation on all queries

## 📈 Future Enhancements
- Real-time data streaming
- Custom query templates
- Data visualization tools
- Automated alerts
- Performance monitoring

## 🐛 Troubleshooting
- Check authentication status
- Verify database connection
- Review query syntax
- Check API response format

---
*Last Updated: [Current Date]*
*Status: In Development*
