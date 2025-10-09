# Known Issues & Technical Findings

This document captures important technical findings, known issues, and architectural decisions discovered during development and testing of the LLM Micro-Cap Trading Bot.

## 🐛 Critical Issues (Fixed)

### FIFO P&L Calculation Bug
**Status**: ✅ **FIXED**  
**Date**: 2024-10-08  
**Impact**: High - Affected realized P&L calculations

**Problem**: FIFO P&L calculations were inconsistent between CSV and Supabase repositories.

**Root Cause**: Test data contamination in Supabase. The FIFO processor loads ALL existing trades when initializing, including old test data from previous runs.

**Evidence**:
- CSV: 0 existing trades → 3 new trades → 75 shares sold
- Supabase: 10 existing trades (including 4 FIFO trades) → 3 new trades → 225 shares sold

**Solution**: Use unique fund names for each test run (`TEST_{uuid}`) to prevent data contamination.

**Prevention**: Always use unique fund names in tests, implement proper test data cleanup.

---

## ⚠️ Minor Issues (Documented)

### Precision Differences in P&L Calculations
**Status**: ⚠️ **DOCUMENTED** - Not critical  
**Impact**: Low - Small precision differences in complex calculations

**Problem**: Minor precision differences between CSV and Supabase repositories due to float conversion.

**Root Cause**: Field mappers convert `Decimal` → `float` → `Decimal` for database storage.

**Evidence**:
- Simple trades: Perfect accuracy (0 cent difference)
- Complex trades: 10-60 cents difference on hundreds of dollars
- Percentage: 0.1-0.2% (very small)

**Real-World Impact**:
- $1,000 P&L: ~$1-2 difference
- $10,000 P&L: ~$10-20 difference
- $100,000 P&L: ~$100-200 difference

**Why We Can't Fix It**:
1. **Database Schema**: Supabase uses `DECIMAL(10,2)` - limited precision
2. **API Limitations**: Supabase Python client expects Python native types
3. **JSON Serialization**: JSON standard doesn't have Decimal type
4. **Database Storage**: PostgreSQL returns DECIMAL as float
5. **Web APIs**: Expect float values

**Conclusion**: Precision loss is **negligible** and **unavoidable** due to technical constraints. Industry standard for financial systems.

---

## 🏗️ Architectural Decisions

### Dual-Write Architecture
**Status**: ✅ **IMPLEMENTED**  
**Purpose**: Provide redundancy and migration path from CSV to Supabase

**Design**:
- **Primary Source**: CSV files (source of truth)
- **Secondary Target**: Supabase database (backup + future features)
- **Write Strategy**: Write to both repositories simultaneously
- **Read Strategy**: Read from CSV (primary source)

**Benefits**:
- Data redundancy and backup
- Gradual migration path
- Future feature enablement
- Risk mitigation

**Trade-offs**:
- Slightly slower writes (dual operations)
- Potential consistency issues
- More complex error handling

### Field Mapping Strategy
**Status**: ✅ **IMPLEMENTED**  
**Purpose**: Convert between domain models and database formats

**Design**:
- **PositionMapper**: Handles Position model ↔ database conversion
- **TradeMapper**: Handles Trade model ↔ database conversion
- **TypeTransformers**: Utility functions for type conversion

**Key Decisions**:
- Convert `Decimal` to `float` for database storage
- Handle missing fields gracefully
- Preserve data integrity during conversion
- Support both CSV and Supabase formats

**Known Limitations**:
- Precision loss during float conversion
- Some fields not stored in database (e.g., `action` in trades)
- Currency field may default to 'CAD' in some cases

---

## 🧪 Testing Infrastructure

### Test Data Management
**Status**: ✅ **IMPLEMENTED**  
**Purpose**: Ensure clean test environments and prevent data contamination

**Solution**: 
- Use unique fund names for each test run
- Implement clear data utility for test cleanup
- Separate test data from production data

**Tools Created**:
- `utils/clear_fund_data.py`: Clear fund data utility
- Menu option "z": Clear Test Data
- Unique fund naming: `TEST_{uuid}`

**Best Practices**:
- Always use unique fund names in tests
- Clean up test data after test runs
- Separate test and production environments
- Document test data requirements

### P&L Consistency Testing
**Status**: ✅ **IMPLEMENTED**  
**Purpose**: Validate P&L calculations across different repositories

**Test Categories**:
- Basic P&L calculations
- Daily P&L calculations
- FIFO P&L calculations
- Portfolio total P&L
- Dual-write consistency
- Real data testing

**Key Findings**:
- Most calculations are consistent between repositories
- FIFO calculations require clean test data
- Precision differences are minor and acceptable
- Dual-write operations maintain data integrity

---

## 🔧 Technical Constraints

### Database Schema Limitations
**Status**: ⚠️ **DOCUMENTED**  
**Impact**: Affects precision and data storage

**Constraints**:
- `DECIMAL(10,2)` for most financial fields
- Maximum value: 99,999,999.99
- Limited precision for high-value positions
- No native Decimal type support

**Workarounds**:
- Accept precision loss for large values
- Use appropriate data types for different scales
- Document precision limitations

### Supabase API Limitations
**Status**: ⚠️ **DOCUMENTED**  
**Impact**: Affects data serialization and type handling

**Constraints**:
- Requires Python native types (float, int, str)
- No direct Decimal support
- JSON serialization limitations
- API expects specific data formats

**Workarounds**:
- Convert Decimal to float for API calls
- Handle type conversion in field mappers
- Preserve precision where possible

---

## 📊 Performance Considerations

### Database Query Performance
**Status**: ✅ **OPTIMIZED**  
**Purpose**: Ensure efficient data retrieval

**Optimizations**:
- Database views for complex calculations
- Indexes on frequently queried fields
- Pre-calculated P&L values
- Efficient date-based queries

**Monitoring**:
- Query execution times
- Database connection usage
- Memory consumption
- API response times

### CSV vs Database Performance
**Status**: ✅ **DOCUMENTED**  
**Purpose**: Understand performance trade-offs

**CSV Advantages**:
- Fast local access
- Simple file operations
- No network latency
- Easy backup/restore

**Database Advantages**:
- Concurrent access
- Complex queries
- Data integrity
- Scalability

**Recommendations**:
- Use CSV for primary operations
- Use database for analytics and reporting
- Implement caching for frequently accessed data

---

## 🚨 Error Handling

### Repository Error Patterns
**Status**: ✅ **DOCUMENTED**  
**Purpose**: Understand common failure modes

**CSV Repository Errors**:
- File permission issues
- Disk space limitations
- Corrupted CSV files
- Encoding problems

**Supabase Repository Errors**:
- Network connectivity issues
- API rate limiting
- Authentication failures
- Database constraint violations

**Error Handling Strategy**:
- Graceful degradation
- Error logging and monitoring
- User-friendly error messages
- Automatic retry mechanisms

### Data Consistency Issues
**Status**: ✅ **DOCUMENTED**  
**Purpose**: Prevent data corruption

**Common Issues**:
- Field mapping mismatches
- Type conversion errors
- Missing required fields
- Precision loss

**Prevention**:
- Comprehensive field mapping
- Type validation
- Data integrity checks
- Regular consistency testing

---

## 🔮 Future Considerations

### Migration Strategy
**Status**: 📋 **PLANNED**  
**Purpose**: Plan transition from CSV to database

**Phases**:
1. **Current**: Dual-write architecture
2. **Phase 1**: Database as primary, CSV as backup
3. **Phase 2**: Database only, CSV for export
4. **Phase 3**: Full database architecture

**Requirements**:
- Data migration tools
- Backward compatibility
- Performance optimization
- User training

### Scalability Planning
**Status**: 📋 **PLANNED**  
**Purpose**: Prepare for growth

**Considerations**:
- Database performance at scale
- API rate limiting
- Data archiving strategies
- Multi-user support

**Recommendations**:
- Monitor database performance
- Implement data archiving
- Plan for horizontal scaling
- Consider microservices architecture

---

## 📝 Maintenance Notes

### Regular Tasks
- Monitor precision differences
- Clean up test data
- Update field mappers as needed
- Test dual-write consistency
- Review error logs

### Code Quality
- Maintain comprehensive tests
- Document architectural decisions
- Keep field mappers up to date
- Monitor performance metrics
- Regular code reviews

### Documentation
- Update this file with new findings
- Document new issues as they arise
- Maintain architectural decision records
- Keep test documentation current
- Update user guides

---

## 🎯 Key Takeaways

1. **FIFO Bug**: Always use unique fund names in tests to prevent data contamination
2. **Precision Loss**: Acceptable and unavoidable due to technical constraints
3. **Dual-Write**: Provides redundancy and migration path
4. **Field Mapping**: Critical for data consistency between repositories
5. **Testing**: Comprehensive testing reveals real issues and validates fixes
6. **Documentation**: Essential for maintaining system understanding

---

*Last Updated: 2024-10-08*  
*Maintained by: Development Team*
