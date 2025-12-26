# Chain of Thought RAG Upgrade - Test Plan

## Overview
Test the Level 2 RAG upgrade (Chain of Thought analysis) by re-analyzing existing articles and verifying that the new fields are correctly populated and displayed.

## Prerequisites
- ✅ Database migration completed (`15_add_chain_of_thought_fields.sql`)
- ✅ Ollama running and accessible
- ✅ At least 2-3 articles in the database to test with
- ✅ Admin access to the Research page

## Test Steps

### 1. Verify Database Schema
**Goal:** Confirm new columns exist in database

**Steps:**
1. Run verification script:
   ```bash
   python web_dashboard/scripts/verify_migration.py
   ```

**Expected Result:**
- All 5 new columns present: `claims`, `fact_check`, `conclusion`, `sentiment`, `sentiment_score`
- All 3 new indexes present

---

### 2. Re-Analyze Articles via Web UI
**Goal:** Test that re-analysis populates new fields correctly

**Steps:**
1. Navigate to Research page in web dashboard
2. Find 2-3 articles that have content but may not have Chain of Thought fields yet
3. As admin, use the sidebar "Re-Analyze Selected" feature:
   - Select articles using checkboxes
   - Choose a model (e.g., `llama3.2:3b`)
   - Click "🔄 Re-Analyze Selected"
4. Wait for completion

**Expected Result:**
- Success message: "✅ Re-analyzed X article(s)"
- No errors in the process

---

### 3. Verify Fields in Database
**Goal:** Confirm new fields were saved to database

**Steps:**
1. Query database directly:
   ```sql
   SELECT id, title, sentiment, sentiment_score, 
          claims, fact_check, conclusion
   FROM research_articles
   WHERE sentiment IS NOT NULL
   LIMIT 3;
   ```

**Expected Result:**
- `sentiment` is one of: VERY_BULLISH, BULLISH, NEUTRAL, BEARISH, VERY_BEARISH
- `sentiment_score` matches sentiment:
  - VERY_BULLISH = 2.0
  - BULLISH = 1.0
  - NEUTRAL = 0.0
  - BEARISH = -1.0
  - VERY_BEARISH = -2.0
- `claims` is a JSON array (or NULL)
- `fact_check` is text (or NULL)
- `conclusion` is text (or NULL)

---

### 4. Verify UI Display
**Goal:** Confirm new fields are visible in article view

**Steps:**
1. On Research page, expand one of the re-analyzed articles
2. Check for new sections:
   - **Sentiment badge** at top (with icon and score)
   - **Chain of Thought Analysis** section with:
     - Claims Identified (numbered list)
     - Fact Check (text)
     - Conclusion (text)

**Expected Result:**
- Sentiment badge displays with correct icon:
  - 🟢 VERY_BULLISH
  - 🟡 BULLISH
  - ⚪ NEUTRAL
  - 🟠 BEARISH
  - 🔴 VERY_BEARISH
- Sentiment score shown in parentheses
- Claims displayed as numbered list (if available)
- Fact check and conclusion displayed as text (if available)

---

### 5. Test Sentiment Score Calculations
**Goal:** Verify sentiment_score enables efficient database queries

**Steps:**
1. Run SQL query to calculate average sentiment:
   ```sql
   SELECT AVG(sentiment_score) as avg_sentiment
   FROM research_articles
   WHERE sentiment_score IS NOT NULL;
   ```

2. Test filtering by sentiment:
   ```sql
   SELECT COUNT(*) as bullish_count
   FROM research_articles
   WHERE sentiment_score > 0.5;
   ```

**Expected Result:**
- Average sentiment calculated without CASE WHEN statements
- Filtering by sentiment_score works efficiently
- Results make sense (e.g., average near 0 if mostly NEUTRAL)

---

### 6. Test Edge Cases
**Goal:** Verify handling of missing/invalid data

**Test Cases:**
1. **Article with no sentiment** - Should display normally without sentiment badge
2. **Article with claims but no fact_check** - Should show claims, skip fact_check
3. **Article with empty claims array** - Should not show claims section
4. **Invalid sentiment value** - Should default to NEUTRAL (0.0)

**Expected Result:**
- UI gracefully handles missing fields
- No errors or crashes
- Sections only appear when data is available

---

## Success Criteria

✅ **All tests pass if:**
1. Re-analysis successfully populates all new fields
2. Sentiment and sentiment_score are correctly calculated and stored
3. UI displays all new fields correctly
4. Database queries using sentiment_score work efficiently
5. Edge cases handled gracefully

---

## Troubleshooting

### Issue: Re-analysis doesn't save new fields
**Check:**
- Verify `update_article_analysis()` includes new parameters
- Check database logs for UPDATE query
- Verify Ollama is returning new fields in summary_data

### Issue: UI doesn't show new fields
**Check:**
- Verify SELECT queries include new columns
- Check browser console for errors
- Verify article data includes new fields (use browser dev tools)

### Issue: Sentiment score doesn't match sentiment
**Check:**
- Verify sentiment_score_map in `ollama_client.py`
- Check that sentiment validation is working
- Verify database column types (sentiment_score should be FLOAT)

---

## Next Steps After Testing

Once testing is complete:
1. Monitor production articles for sentiment distribution
2. Consider adding sentiment filtering to article search
3. Plan tier 2 analysis for BULLISH/VERY_BULLISH articles
4. Consider adding sentiment trends/charts to dashboard

