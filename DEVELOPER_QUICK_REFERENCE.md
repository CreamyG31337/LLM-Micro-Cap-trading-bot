# Developer Quick Reference

Quick reference for common issues and solutions in the LLM Micro-Cap Trading Bot.

## 🚨 Critical Issues & Solutions

### FIFO P&L Calculation Bug
**Problem**: FIFO calculations inconsistent between CSV and Supabase  
**Solution**: Use unique fund names in tests (`TEST_{uuid}`)  
**Prevention**: Always clean test data, use unique fund names

### Precision Differences
**Problem**: Small precision differences in P&L calculations  
**Status**: Acceptable - caused by float conversion requirements  
**Impact**: < 1 cent on normal trades, < 0.2% of total value

## 🛠️ Common Commands

### Clear Test Data
```bash
# List fund data
python utils/clear_fund_data.py --fund test --data-dir "trading_data/funds/TEST" --list

# Clear fund data (with confirmation)
python utils/clear_fund_data.py --fund test --data-dir "trading_data/funds/TEST" --confirm
```

### Run P&L Tests
```bash
# Test basic P&L consistency
python -m pytest tests/test_pnl_calculation_consistency.py::TestPnLCalculationConsistency::test_basic_pnl_calculation_consistency -v

# Test FIFO P&L consistency
python -m pytest tests/test_pnl_calculation_consistency.py::TestPnLCalculationConsistency::test_fifo_pnl_calculation_consistency -v

# Test with real data
python -m pytest tests/test_real_data_pnl_consistency.py -v
```

### Debug Precision Issues
```bash
# Analyze precision errors
python debug/analyze_precision_errors.py

# Analyze float conversion necessity
python debug/analyze_float_conversion_necessity.py
```

## 📊 Test Data Management

### Unique Fund Names
```python
import uuid
test_fund = f"TEST_{uuid.uuid4().hex[:8]}"
```

### Clean Test Environment
```python
# Always use unique fund names
# Clean up test data after tests
# Separate test and production data
```

## 🔍 Debugging Tips

### FIFO Issues
1. Check for existing trades in Supabase
2. Use unique fund names
3. Verify lot tracker initialization
4. Check trade history consistency

### Precision Issues
1. Check field mapper conversions
2. Verify database schema constraints
3. Test with different decimal precisions
4. Monitor float conversion impact

### Dual-Write Issues
1. Verify both repositories are accessible
2. Check field mapping consistency
3. Test error handling scenarios
4. Monitor write coordination

## 📋 Field Mapping Reference

### PositionMapper
- **model_to_db**: Converts Position → database format
- **db_to_model**: Converts database → Position format
- **Key Fields**: shares, price, cost_basis, pnl, currency

### TradeMapper
- **model_to_db**: Converts Trade → database format
- **db_to_model**: Converts database → Trade format
- **Key Fields**: ticker, action, shares, price, currency

### Common Issues
- Currency field may default to 'CAD'
- Action field not stored in database
- Precision loss during float conversion

## 🎯 Best Practices

### Testing
- Use unique fund names for each test
- Clean up test data after tests
- Test both CSV and Supabase repositories
- Verify P&L consistency

### Development
- Always test field mappers
- Monitor precision differences
- Document architectural decisions
- Keep tests comprehensive

### Error Handling
- Graceful degradation
- Comprehensive error logging
- User-friendly error messages
- Automatic retry mechanisms

## 🔧 Architecture Quick Reference

### Repository Pattern
- **BaseRepository**: Abstract base class
- **CSVRepository**: File-based storage
- **SupabaseRepository**: Database storage
- **DualWriteRepository**: Dual-write coordinator

### Field Mappers
- **PositionMapper**: Position model ↔ database
- **TradeMapper**: Trade model ↔ database
- **CashBalanceMapper**: Cash balance ↔ database

### Data Flow
1. Domain models (Decimal precision)
2. Field mappers (Decimal → float)
3. Database storage (DECIMAL(10,2))
4. Field mappers (float → Decimal)
5. Domain models (restored precision)

## 📊 Performance Monitoring

### Key Metrics
- P&L calculation accuracy
- Database query performance
- Field mapping efficiency
- Dual-write consistency

### Monitoring Tools
- Precision error analysis
- Performance testing
- Consistency validation
- Error rate monitoring

## 🚀 Quick Fixes

### FIFO Bug
```python
# Use unique fund names
test_fund = f"TEST_{uuid.uuid4().hex[:8]}"
```

### Precision Issues
```python
# Accept minor precision differences
# Document precision limitations
# Use appropriate data types
```

### Test Data Cleanup
```python
# Clear test data
python utils/clear_fund_data.py --fund test --data-dir "trading_data/funds/TEST" --confirm
```

---

*For detailed information, see KNOWN_ISSUES.md*  
*Last Updated: 2024-10-08*
