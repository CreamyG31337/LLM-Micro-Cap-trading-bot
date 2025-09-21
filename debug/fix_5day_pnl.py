                        else:
                            # Use cached historical data instead of fetching again
                            cached_hist = price_cache.get_cached_price(position.ticker)
                            if args.non_interactive:
                                with open('debug_output.txt', 'a') as debug_file:
                                    debug_file.write(f"    {position.ticker}: Cache lookup - found data: {cached_hist is not None and not cached_hist.empty if cached_hist is not None else 'None'}\\n")
                                    debug_file.flush()

                            if (cached_hist is not None
                                and isinstance(cached_hist, pd.DataFrame)
                                and not cached_hist.empty
                                and 'Close' in cached_hist.columns):
                                if args.non_interactive:
                                    with open('debug_output.txt', 'a') as debug_file:
                                        debug_file.write(f"      {position.ticker}: Cache validation passed\\n")
                                        debug_file.flush()

                                closes_series = cached_hist['Close']
                                logger.debug(f"{position.ticker}: Using cached historical closes ({len(closes_series)} days)")
                                
                                # Need at least 6 trading days of data (5 days ago + today)
                                if args.non_interactive:
                                    with open('debug_output.txt', 'a') as debug_file:
                                        debug_file.write(f"      {position.ticker}: Has {len(closes_series)} days of data\\n")
                                        debug_file.flush()
                                if len(closes_series) >= 6:
                                    # Get price from 5 trading days ago (6th from last)
                                    start_price_5d_float = closes_series.iloc[-6]
                                    # Convert to Decimal to match position.current_price type
                                    start_price_5d = Decimal(str(start_price_5d_float))
                                    current_price = position.current_price
                                    
                                    logger.debug(f"{position.ticker}: 5-day ago price: ${start_price_5d:.2f}, current: ${current_price:.2f}")
                                    
                                    # Calculate P&L from 5 trading days ago to current price
                                    # Ensure all inputs are Decimal type for financial calculations
                                    period = pnl_calculator.calculate_period_pnl(
                                        current_price,
                                        start_price_5d,
                                        position.shares,
                                        period_name="five_day"
                                    )
                                    
                                    abs_pnl = period.get('five_day_absolute_pnl')
                                    pct_pnl = period.get('five_day_percentage_pnl')
                                    
                                    if abs_pnl is not None and pct_pnl is not None:
                                        # Format like the daily P&L: "$123.45 +1.2%" or "-$123.45 -1.2%"
                                        pct_value = float(pct_pnl) * 100
                                        if abs_pnl >= 0:
                                            pos_dict['five_day_pnl'] = f"${abs_pnl:.2f} +{pct_value:.1f}%"
                                        else:
                                            pos_dict['five_day_pnl'] = f"-${abs(abs_pnl):.2f} {pct_value:.1f}%"
                                        
                                        if args.non_interactive:
                                            with open('debug_output.txt', 'a') as debug_file:
                                                debug_file.write(f"        {position.ticker}: ✓ 5-day P&L calculated: {pos_dict['five_day_pnl']}\\n")
                                                debug_file.flush()
                                        logger.debug(f"{position.ticker}: 5-day P&L calculated: {pos_dict['five_day_pnl']}")
                                    else:
                                        pos_dict['five_day_pnl'] = "N/A"
                                        logger.debug(f"{position.ticker}: P&L calculation returned None")
                                else:
                                    pos_dict['five_day_pnl'] = "N/A"
                                    if args.non_interactive:
                                        with open('debug_output.txt', 'a') as debug_file:
                                            debug_file.write(f"      {position.ticker}: ✗ Insufficient historical data ({len(closes_series)} < 6)\\n")
                                            debug_file.flush()
                                    logger.debug(f"{position.ticker}: Insufficient historical data ({len(closes_series)} < 6)")
                            else:
                                pos_dict['five_day_pnl'] = "N/A"
                                if args.non_interactive:
                                    with open('debug_output.txt', 'a') as debug_file:
                                        debug_file.write(f"      {position.ticker}: ✗ Cache validation failed\\n")
                                        debug_file.flush()
                                logger.debug(f"{position.ticker}: No price data available")