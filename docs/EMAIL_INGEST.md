# Email Trade Ingestion (Menu option "e")

This tool lets you paste one or more trade notification emails and append normalized trades into your trade log (llm_trade_log.csv). It does NOT write directly to the portfolio snapshot. After you’re done adding emails, you can rebuild the portfolio snapshot from the trade log.

Key behaviors
- Multiple emails per session: paste an email, confirm the parsed trade, repeat as needed
- Idempotency: duplicate trades are detected and skipped (same ticker, action, shares, price, and timestamp within ±5 minutes)
- Rebuild prompt: after saving any trades, you can trigger a full portfolio rebuild from the trade log
- Caching: company names and market data use persistent caches to reduce API calls

Usage
- From the menu: choose e "Add Trade from Email"
- Default (no flags): multi-email session. Finish each email with END on a line by itself. Type DONE when finished.
- Single email modes:
  - Interactive (single): python add_trade_from_email.py --interactive --data-dir "my trading"
  - From text: python add_trade_from_email.py --text "...email body..." --data-dir "my trading"
  - From file: python add_trade_from_email.py --file email.txt --data-dir "my trading"
- Test/dry-run (no writes): add --test to parse and preview only

How duplicates are detected
A new trade is considered duplicate if a previous trade exists with all of:
- Same ticker (case-insensitive)
- Same action (BUY/SELL)
- Shares equal within 1e-6
- Price equal within 1e-6
- Timestamp within ±5 minutes

What gets written
- Each confirmed trade is appended to llm_trade_log.csv
- The portfolio snapshot is not modified here to preserve FIFO/cost-basis logic
- After the session, choose to rebuild the portfolio CSV from the trade log for a consistent snapshot

Caching
- Market data is cached by PriceCache to avoid repeated downloads
- Fundamentals are cached to .cache/fundamentals_cache.json with a configurable TTL (default 12h)
- Company names are cached persistently via PriceCache so they aren’t fetched repeatedly

Tips
- Use the multi-email mode for fast capture of multiple fill emails
- If you accidentally paste the same email twice, the duplicate will be detected and skipped
- You can safely rebuild multiple times; caches minimize API calls after the first run
