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