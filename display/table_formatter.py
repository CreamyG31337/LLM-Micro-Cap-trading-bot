"""Table formatter module for Rich table formatting and portfolio display.

This module provides table formatting functionality using Rich tables with fallback
to plain text display. It includes JSON output capability for future web dashboard API
and handles data from any repository type.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union

# Optional pandas import
try:
    import pandas as pd
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False
    pd = None

# Import display utilities
from .console_output import print_info, get_console, has_rich_support
from .terminal_utils import get_optimal_table_width, is_using_test_data

# Rich imports with fallback
try:
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

# Colorama imports for fallback
try:
    from colorama import Fore, Style
except ImportError:
    class DummyColor:
        def __getattr__(self, name):
            return ""
    Fore = Style = DummyColor()


class TableFormatter:
    """Table formatter class for creating portfolio and financial tables.
    
    This class handles both Rich table formatting and plain text fallback,
    with JSON output capability for future web dashboard integration.
    """
    
    def __init__(self, data_dir: Optional[str] = None, web_mode: bool = False):
        """Initialize the table formatter.
        
        Args:
            data_dir: Optional data directory path for context
            web_mode: Whether to optimize for web display
        """
        self.data_dir = data_dir
        self.web_mode = web_mode
        self.console = get_console()
        self.optimal_width = get_optimal_table_width(data_dir)
        self.using_test_data = is_using_test_data(data_dir)
    
    def create_portfolio_table(self, portfolio_data: Union[List[Dict[str, Any]], 'pd.DataFrame'], 
                             current_date: Optional[str] = None,
                             output_format: str = "display") -> Optional[str]:
        """Create a portfolio table display with current prices, P&L, and position weights.
        
        Args:
            portfolio_data: List of portfolio position dictionaries OR pandas DataFrame (for backward compatibility)
            current_date: Optional current date string for title
            output_format: Output format - "display", "json", or "html"
            
        Returns:
            JSON string if output_format is "json", None otherwise
        """
        # Handle pandas DataFrame input for backward compatibility
        if _HAS_PANDAS and hasattr(portfolio_data, 'empty'):
            if portfolio_data.empty:
                print_info("Portfolio is currently empty")
                return None if output_format == "display" else json.dumps({"portfolio": []})
            # Convert DataFrame to list of dictionaries
            portfolio_data = portfolio_data.to_dict('records')
        elif not portfolio_data:
            print_info("Portfolio is currently empty")
            return None if output_format == "display" else json.dumps({"portfolio": []})
        
        # Prepare data for different output formats
        if output_format == "json":
            return self._create_portfolio_json(portfolio_data, current_date)
        elif output_format == "html":
            return self._create_portfolio_html(portfolio_data, current_date)
        else:
            return self._create_portfolio_display(portfolio_data, current_date)
    
    def _create_portfolio_display(self, portfolio_data: List[Dict[str, Any]], 
                                current_date: Optional[str] = None) -> None:
        """Create portfolio table for console display."""
        if not current_date:
            current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create safe table title for environments that can't handle Unicode
        from display.console_output import _safe_emoji
        safe_chart_emoji = _safe_emoji("📊")
        table_title = f"{safe_chart_emoji} Portfolio Snapshot - {current_date}"
        
        if has_rich_support() and self.console:
            self._create_rich_portfolio_table(portfolio_data, table_title)
        else:
            self._create_plain_portfolio_table(portfolio_data, table_title)
    
    def _create_rich_portfolio_table(self, portfolio_data: List[Dict[str, Any]], 
                                   table_title: str) -> None:
        """Create Rich-formatted portfolio table."""
        # Import safe emoji function
        from display.console_output import _safe_emoji
        
        # Determine optimal column widths based on environment
        company_max_width = 25 if self.optimal_width >= 140 else 15
        if self.using_test_data:
            company_max_width = 12  # Even more conservative for test data
        
        table = Table(title=table_title, show_header=True, header_style="bold magenta")
        # Create safe column headers (headers can wrap, data stays no_wrap where appropriate)
        table.add_column(f"{_safe_emoji('🎯')}\nTicker", style="cyan", no_wrap=True, width=10, header_style="bold magenta")
        table.add_column(f"{_safe_emoji('🏢')}\nCompany", style="white", no_wrap=True, max_width=company_max_width, justify="left", header_style="bold magenta")
        table.add_column(f"{_safe_emoji('📅')}\nOpened", style="dim", no_wrap=True, width=11, header_style="bold magenta")
        table.add_column(f"{_safe_emoji('📈')}\nShares", justify="right", style="green", width=10, header_style="bold magenta")
        table.add_column(f"{_safe_emoji('💵')}\nPrice", justify="right", style="blue", width=10, header_style="bold magenta")
        table.add_column(f"{_safe_emoji('💰')}\nCurrent", justify="right", style="yellow", width=10, header_style="bold magenta")
        table.add_column(f"{_safe_emoji('💵')}\nTotal Value", justify="right", style="yellow", width=12, header_style="bold magenta")
        table.add_column(f"{_safe_emoji('📊')}\nTotal P&L", justify="right", style="magenta", width=16, header_style="bold magenta")
        table.add_column(f"{_safe_emoji('📈')}\nDaily P&L", justify="right", style="cyan", width=15, header_style="bold magenta")
        table.add_column(f"{_safe_emoji('📊')}\n5-Day P&L", justify="right", style="bright_magenta", width=10, header_style="bold magenta")
        table.add_column(f"{_safe_emoji('🍕')}\nWght", justify="right", style="bright_blue", width=8, header_style="bold magenta")
        table.add_column(f"{_safe_emoji('🛑')}\nStop Loss", justify="right", style="red", width=9, header_style="bold magenta")
        table.add_column(f"{_safe_emoji('💵')}\nCost Basis", justify="right", style="yellow", width=11, header_style="bold magenta")
        
        def format_shares(shares_value):
            """Format shares with up to 6 significant digits, adjusting decimals based on magnitude."""
            if shares_value == 0:
                return "0"
            
            shares = float(shares_value)
            if shares >= 1000:
                # For 1000+: show no decimals (e.g., 1234)
                return f"{shares:.0f}"
            elif shares >= 100:
                # For 100-999: show 3 decimals max (e.g., 123.456)
                return f"{shares:.3f}".rstrip('0').rstrip('.')
            elif shares >= 10:
                # For 10-99: show 4 decimals max (e.g., 12.3456)
                return f"{shares:.4f}".rstrip('0').rstrip('.')
            elif shares >= 1:
                # For 1-9: show 5 decimals max (e.g., 1.23456)
                return f"{shares:.5f}".rstrip('0').rstrip('.')
            else:
                # For <1: show 6 decimals max (e.g., 0.123456)
                return f"{shares:.6f}".rstrip('0').rstrip('.')
        
        for position in portfolio_data:
            # Truncate long company names for display
            company_name = position.get('company', 'N/A')
            display_name = (company_name[:company_max_width-3] + "..." 
                          if len(company_name) > company_max_width else company_name)
            
            # Calculate total value
            shares = float(position.get('shares', 0))
            current_price = float(position.get('current_price', 0)) if position.get('current_price', 0) > 0 else 0
            total_value = shares * current_price if current_price > 0 else 0
            total_value_display = f"${total_value:.2f}" if total_value > 0 else "N/A"

            # Calculate P&L values
            unrealized_pnl = position.get('unrealized_pnl', 0) or 0
            cost_basis = position.get('cost_basis', 0) or 0
            avg_price = position.get('avg_price', 0) or 0
            
            # Calculate total P&L percentage with color coding (dollar amount first, then percentage)
            if cost_basis > 0:
                total_pnl_pct = (unrealized_pnl / cost_basis) * 100
                if total_pnl_pct > 0:
                    total_pnl_display = f"[green]${unrealized_pnl:,.2f} +{total_pnl_pct:.1f}%[/green]"
                elif total_pnl_pct < 0:
                    total_pnl_display = f"[red]${abs(unrealized_pnl):,.2f} {total_pnl_pct:.1f}%[/red]"
                else:
                    total_pnl_display = f"${unrealized_pnl:,.2f} {total_pnl_pct:.1f}%"
            elif avg_price > 0 and current_price > 0:
                total_pnl_pct = ((current_price - avg_price) / avg_price) * 100
                if total_pnl_pct > 0:
                    total_pnl_display = f"[green]${unrealized_pnl:,.2f} +{total_pnl_pct:.1f}%[/green]"
                elif total_pnl_pct < 0:
                    total_pnl_display = f"[red]${abs(unrealized_pnl):,.2f} {total_pnl_pct:.1f}%[/red]"
                else:
                    total_pnl_display = f"${unrealized_pnl:,.2f} {total_pnl_pct:.1f}%"
            else:
                total_pnl_display = 'N/A'

            # Daily P&L (already calculated in trading_script.py as dollar amount)
            daily_pnl_dollar = position.get('daily_pnl', 'N/A')
            if daily_pnl_dollar != 'N/A' and daily_pnl_dollar != '$0.00':
                # Extract numeric value from daily_pnl_dollar (remove $ and convert to float)
                daily_pnl_value = float(daily_pnl_dollar.replace('$', '').replace(',', '').replace('*', ''))

                # Calculate daily P&L percentage based on the dollar amount and total position value
                total_position_value = shares * current_price if current_price > 0 else 0
                daily_pnl_pct = (daily_pnl_value / total_position_value * 100) if total_position_value > 0 else 0

                if daily_pnl_pct > 0:
                    daily_pnl_display = f"[green]${daily_pnl_value:,.2f} +{daily_pnl_pct:.1f}%[/green]"
                elif daily_pnl_pct < 0:
                    daily_pnl_display = f"[red]${abs(daily_pnl_value):,.2f} {daily_pnl_pct:.1f}%[/red]"
                else:
                    daily_pnl_display = f"${daily_pnl_value:,.2f} {daily_pnl_pct:.1f}%"
            else:
                # When daily P&L is $0.00, percentage should also be 0.00%
                daily_pnl_display = "$0.00 0.0%"
            
            # Get position weight from enhanced data
            weight_display = position.get('position_weight', 'N/A')
            
            table.add_row(
                position.get('ticker', 'N/A'),
                display_name,
                position.get('opened_date', 'N/A'),
                format_shares(position.get('shares', 0)),
                f"${float(position.get('avg_price', 0)):.2f}",  # Fixed field name
                f"${float(position.get('current_price', 0)):.2f}" if position.get('current_price', 0) > 0 else "N/A",
                total_value_display,  # Total Value (shares * current price)
                total_pnl_display,  # Combined Total P&L: percentage [dollar amount]
                daily_pnl_display,  # Combined Daily P&L: percentage [dollar amount]
                position.get('five_day_pnl', 'N/A'),  # 5-day P&L from enhanced data
                weight_display,  # Position weight from enhanced data
                f"${float(position.get('stop_loss', 0)):.2f}" if position.get('stop_loss', 0) > 0 else "None",
                f"${float(position.get('cost_basis', 0)):.2f}"
            )
        
        self.console.print(table)
    
    def _create_plain_portfolio_table(self, portfolio_data: List[Dict[str, Any]], 
                                    table_title: str) -> None:
        """Create plain text portfolio table."""
        print(f"\\n{Fore.MAGENTA}{table_title}:{Style.RESET_ALL}")
        
        def format_shares_plain(shares_value):
            """Format shares with up to 6 significant digits, adjusting decimals based on magnitude."""
            if shares_value == 0:
                return "0"
            
            shares = float(shares_value)
            if shares >= 1000:
                # For 1000+: show no decimals (e.g., 1234)
                return f"{shares:.0f}"
            elif shares >= 100:
                # For 100-999: show 3 decimals max (e.g., 123.456)
                return f"{shares:.3f}".rstrip('0').rstrip('.')
            elif shares >= 10:
                # For 10-99: show 4 decimals max (e.g., 12.3456)
                return f"{shares:.4f}".rstrip('0').rstrip('.')
            elif shares >= 1:
                # For 1-9: show 5 decimals max (e.g., 1.23456)
                return f"{shares:.5f}".rstrip('0').rstrip('.')
            else:
                # For <1: show 6 decimals max (e.g., 0.123456)
                return f"{shares:.6f}".rstrip('0').rstrip('.')
        
        # Convert to DataFrame for better plain text formatting
        df_data = []
        for position in portfolio_data:
            # Calculate values
            shares = float(position.get('shares', 0))
            current_price = float(position.get('current_price', 0)) if position.get('current_price', 0) > 0 else 0
            avg_price = float(position.get('avg_price', 0)) or 0
            cost_basis = float(position.get('cost_basis', 0)) or 0
            unrealized_pnl = float(position.get('unrealized_pnl', 0)) or 0
            total_value = shares * current_price if current_price > 0 else 0
            
            # Calculate P&L percentage with color coding (dollar amount first, then percentage)
            if cost_basis > 0:
                total_pnl_pct = (unrealized_pnl / cost_basis) * 100
                if total_pnl_pct > 0:
                    total_pnl_display = f"{Fore.GREEN}${unrealized_pnl:,.2f} +{total_pnl_pct:.1f}%{Style.RESET_ALL}"
                elif total_pnl_pct < 0:
                    total_pnl_display = f"{Fore.RED}${abs(unrealized_pnl):,.2f} {total_pnl_pct:.1f}%{Style.RESET_ALL}"
                else:
                    total_pnl_display = f"${unrealized_pnl:,.2f} {total_pnl_pct:.1f}%"
            elif avg_price > 0 and current_price > 0:
                total_pnl_pct = ((current_price - avg_price) / avg_price) * 100
                if total_pnl_pct > 0:
                    total_pnl_display = f"{Fore.GREEN}${unrealized_pnl:,.2f} +{total_pnl_pct:.1f}%{Style.RESET_ALL}"
                elif total_pnl_pct < 0:
                    total_pnl_display = f"{Fore.RED}${abs(unrealized_pnl):,.2f} {total_pnl_pct:.1f}%{Style.RESET_ALL}"
                else:
                    total_pnl_display = f"${unrealized_pnl:,.2f} {total_pnl_pct:.1f}%"
            else:
                total_pnl_display = 'N/A'
            
            # Daily P&L with color coding
            daily_pnl_dollar = position.get('daily_pnl', 'N/A')
            if daily_pnl_dollar != 'N/A' and daily_pnl_dollar != '$0.00':
                if avg_price > 0 and current_price > 0:
                    daily_pnl_pct = ((current_price - avg_price) / avg_price) * 100
                    # Extract numeric value from daily_pnl_dollar (remove $ and convert to float)
                    daily_pnl_value = float(daily_pnl_dollar.replace('$', '').replace(',', '').replace('*', ''))
                    if daily_pnl_pct > 0:
                        daily_pnl_display = f"{Fore.GREEN}${daily_pnl_value:,.2f} +{daily_pnl_pct:.1f}%{Style.RESET_ALL}"
                    elif daily_pnl_pct < 0:
                        daily_pnl_display = f"{Fore.RED}${abs(daily_pnl_value):,.2f} {daily_pnl_pct:.1f}%{Style.RESET_ALL}"
                    else:
                        daily_pnl_display = f"${daily_pnl_value:,.2f} {daily_pnl_pct:.1f}%"
                else:
                    daily_pnl_display = f"N/A {daily_pnl_dollar}"
            else:
                daily_pnl_display = daily_pnl_dollar
            
            df_data.append({
                'Ticker': position.get('ticker', 'N/A'),
                'Company': position.get('company', 'N/A'),
                'Opened': position.get('opened_date', 'N/A'),
                'Shares': format_shares_plain(shares),
                'Price': f"${avg_price:.2f}",
                'Current': f"${current_price:.2f}" if current_price > 0 else "N/A",
                'Total Value': f"${total_value:.2f}" if total_value > 0 else "N/A",
                'Dollar P&L': f"${abs(unrealized_pnl):,.2f}" if unrealized_pnl != 0 else "$0.00",
                'Total P&L': total_pnl_display,
                'Daily P&L': daily_pnl_display,
                'Weight': position.get('position_weight', 'N/A'),
                'Stop Loss': f"${float(position.get('stop_loss', 0)):.2f}" if position.get('stop_loss', 0) > 0 else "None",
                'Cost Basis': f"${cost_basis:.2f}"
            })

        if df_data and _HAS_PANDAS:
            df = pd.DataFrame(df_data)

            # Set pandas display options for better formatting
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', self.optimal_width)
            pd.set_option('display.max_colwidth', 18 if self.using_test_data else 20)

            print(df.to_string(index=False))

            # Reset pandas options
            pd.reset_option('display.max_columns')
            pd.reset_option('display.width')
            pd.reset_option('display.max_colwidth')
        elif df_data:
            # Fallback to simple table formatting without pandas
            headers = list(df_data[0].keys()) if df_data else []

            # Print headers
            header_line = " | ".join(f"{header:>12}" for header in headers)
            print(header_line)
            print("-" * len(header_line))

            # Print data rows
            for row in df_data:
                data_line = " | ".join(f"{str(row.get(header, 'N/A')):>12}" for header in headers)
                print(data_line)
    
    def _create_portfolio_json(self, portfolio_data: List[Dict[str, Any]], 
                             current_date: Optional[str] = None) -> str:
        """Create JSON output for portfolio data."""
        output = {
            "timestamp": current_date or datetime.now().isoformat(),
            "portfolio": portfolio_data,
            "metadata": {
                "total_positions": len(portfolio_data),
                "data_source": "csv" if not self.web_mode else "api"
            }
        }
        return json.dumps(output, indent=2)
    
    def _create_portfolio_html(self, portfolio_data: List[Dict[str, Any]], 
                             current_date: Optional[str] = None) -> str:
        """Create HTML table output for web display."""
        html = f"""
        <div class="portfolio-table">
            <h2>📊 Portfolio Snapshot - {current_date or datetime.now().strftime('%Y-%m-%d')}</h2>
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>🎯 Ticker</th>
                        <th>🏢 Company</th>
                        <th>📅 Opened</th>
                        <th>📈 Shares</th>
                        <th>💵 Price</th>
                        <th>💰 Current</th>
                        <th>💵 Total Value</th>
                        <th>📊 Total P&L</th>
                        <th>📈 Daily P&L</th>
                        <th>🍕 Weight</th>
                        <th>🛑 Stop Loss</th>
                        <th>💵 Cost Basis</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for position in portfolio_data:
            # Calculate total value for HTML
            shares = float(position.get('shares', 0))
            current_price = float(position.get('current_price', 0)) if position.get('current_price', 0) > 0 else 0
            total_value = shares * current_price if current_price > 0 else 0

            # Create combined P&L values for HTML
            unrealized_pnl = position.get('unrealized_pnl', 0)
            total_pnl_pct = position.get('total_pnl', 'N/A')
            daily_pnl_pct = position.get('daily_pnl', 'N/A')

            # Combine percentage and dollar amount
            if total_pnl_pct != 'N/A' and unrealized_pnl != 0:
                total_pnl_display = f"{total_pnl_pct} [${unrealized_pnl:+,.2f}]"
            elif total_pnl_pct != 'N/A':
                total_pnl_display = f"{total_pnl_pct} [$0.00]"
            else:
                total_pnl_display = 'N/A'

            if daily_pnl_pct != 'N/A':
                daily_dollar_pnl = 0  # Simplified calculation
                daily_pnl_display = f"{daily_pnl_pct} [${daily_dollar_pnl:+,.2f}]"
            else:
                daily_pnl_display = 'N/A'

            html += f"""
                    <tr>
                        <td>{position.get('ticker', 'N/A')}</td>
                        <td>{position.get('company_name', 'N/A')}</td>
                        <td>{position.get('opened_date', 'N/A')}</td>
                        <td>{float(position.get('shares', 0)):.4f}</td>
                        <td>${float(position.get('avg_price', 0)):.2f}</td>
                        <td>${float(position.get('current_price', 0)):.2f}</td>
                        <td>${total_value:.2f}</td>
                        <td>{total_pnl_display}</td>
                        <td>{daily_pnl_display}</td>
                        <td>{position.get('position_weight', 'N/A')}</td>
                        <td>${float(position.get('stop_loss', 0)):.2f}</td>
                        <td>${float(position.get('cost_basis', 0)):.2f}</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        """
        return html
    
    def create_ownership_table(self, ownership_data: Dict[str, Dict[str, Any]], 
                             output_format: str = "display") -> Optional[str]:
        """Create ownership details table.
        
        Args:
            ownership_data: Dictionary of ownership information by contributor
            output_format: Output format - "display", "json", or "html"
            
        Returns:
            JSON string if output_format is "json", None otherwise
        """
        if output_format == "json":
            return json.dumps({"ownership": ownership_data}, indent=2)
        
        if has_rich_support() and self.console:
            ownership_table = Table(title="Ownership Details", show_header=True, header_style="bold blue")
            ownership_table.add_column("Contributor", style="yellow", no_wrap=True)
            ownership_table.add_column("Shares", justify="right", style="cyan")
            ownership_table.add_column("Contributed", justify="right", style="green")
            ownership_table.add_column("Ownership %", justify="right", style="magenta")
            ownership_table.add_column("Current Value", justify="right", style="red")
            
            # Sort by ownership percentage (highest first)
            sorted_ownership = sorted(ownership_data.items(), 
                                    key=lambda x: x[1].get('ownership_pct', 0), reverse=True)
            
            for contributor, data in sorted_ownership:
                ownership_table.add_row(
                    contributor,
                    f"{data.get('shares', 0):.2f}",
                    f"${data.get('contributed', 0):,.2f}",
                    f"{data.get('ownership_pct', 0):.1f}%",
                    f"${data.get('current_value', 0):,.2f}"
                )
            
            self.console.print(ownership_table)
        else:
            print_info("Ownership Details:", "👥")
            for contributor, data in ownership_data.items():
                print(f"  {contributor}: {data.get('shares', 0):.2f} shares, "
                      f"${data.get('contributed', 0):,.2f} contributed, "
                      f"{data.get('ownership_pct', 0):.1f}% ownership")
        
        return None
    
    def create_statistics_table(self, stats_data: Dict[str, float], 
                              output_format: str = "display") -> Optional[str]:
        """Create portfolio statistics table.
        
        Args:
            stats_data: Dictionary of portfolio statistics
            output_format: Output format - "display", "json", or "html"
            
        Returns:
            JSON string if output_format is "json", None otherwise
        """
        if output_format == "json":
            return json.dumps({"statistics": stats_data}, indent=2)
        
        if has_rich_support() and self.console:
            stats_table = Table(title="📊 Portfolio Statistics", show_header=True, header_style="bold blue")
            stats_table.add_column("Statistic", style="cyan", no_wrap=True)
            stats_table.add_column("Amount", justify="right", style="yellow")

            # Helper function to get color style based on value
            def get_pnl_style(value: float) -> str:
                return "green" if value >= 0 else "red"

            stats_table.add_row("💰 Total Contributions", f"${stats_data.get('total_contributions', 0):,.2f}")
            stats_table.add_row("💵 Total Cost Basis", f"${stats_data.get('total_cost_basis', 0):,.2f}")
            stats_table.add_row("📈 Current Portfolio Value", f"${stats_data.get('total_current_value', 0):,.2f}")
            stats_table.add_row("💹 Unrealized P&L", f"${stats_data.get('total_pnl', 0):,.2f}",
                               style=get_pnl_style(stats_data.get('total_pnl', 0)))
            stats_table.add_row("💰 Realized P&L", f"${stats_data.get('total_realized_pnl', 0):,.2f}",
                               style=get_pnl_style(stats_data.get('total_realized_pnl', 0)))
            stats_table.add_row("📊 Total Portfolio P&L", f"${stats_data.get('total_portfolio_pnl', 0):,.2f}",
                               style=get_pnl_style(stats_data.get('total_portfolio_pnl', 0)))

            self.console.print(stats_table)
        else:
            print_info("Portfolio Statistics:", "📊")

            # Helper function to get color based on value for fallback display
            def get_pnl_color(value: float) -> str:
                return Fore.GREEN if value >= 0 else Fore.RED

            print(f"  Total Contributions: ${stats_data.get('total_contributions', 0):,.2f}")
            print(f"  Total Cost Basis: ${stats_data.get('total_cost_basis', 0):,.2f}")
            print(f"  Current Portfolio Value: ${stats_data.get('total_current_value', 0):,.2f}")

            unrealized_pnl = stats_data.get('total_pnl', 0)
            print(f"  Unrealized P&L: {get_pnl_color(unrealized_pnl)}${unrealized_pnl:,.2f}{Style.RESET_ALL}")

            realized_pnl = stats_data.get('total_realized_pnl', 0)
            print(f"  Realized P&L: {get_pnl_color(realized_pnl)}${realized_pnl:,.2f}{Style.RESET_ALL}")

            total_portfolio_pnl = stats_data.get('total_portfolio_pnl', 0)
            print(f"  Total Portfolio P&L: {get_pnl_color(total_portfolio_pnl)}${total_portfolio_pnl:,.2f}{Style.RESET_ALL}")
        
        return None
    
    def create_summary_table(self, summary_data: Dict[str, float], 
                           output_format: str = "display") -> Optional[str]:
        """Create financial summary table.
        
        Args:
            summary_data: Dictionary of financial summary data
            output_format: Output format - "display", "json", or "html"
            
        Returns:
            JSON string if output_format is "json", None otherwise
        """
        if output_format == "json":
            return json.dumps({"summary": summary_data}, indent=2)
        
        total_value = summary_data.get('portfolio_value', 0)
        total_pnl = summary_data.get('total_pnl', 0)
        cash = summary_data.get('cash_balance', 0)
        fund_total = summary_data.get('fund_contributions', 0)
        
        if has_rich_support() and self.console:
            summary_table = Table(title="💰 Financial Summary", show_header=True, header_style="bold magenta")
            summary_table.add_column("Metric", style="cyan", no_wrap=True)
            summary_table.add_column("Amount", justify="right", style="green")
            
            summary_table.add_row("📊 Portfolio Value", f"${total_value:,.2f}")
            summary_table.add_row("💹 Total P&L", 
                                f"${total_pnl:,.2f}" if total_pnl >= 0 else f"[red]${total_pnl:,.2f}[/red]")
            summary_table.add_row("💰 Cash Balance", f"${cash:,.2f}")
            summary_table.add_row("🏦 Total Equity", f"${total_value + cash:,.2f}")
            summary_table.add_row("💵 Fund Contributions", f"${fund_total:,.2f}")
            
            self.console.print(summary_table)
        else:
            print_info(f"Portfolio Total Value: ${total_value:,.2f}", "📊")
            print(f"  Total P&L: ${total_pnl:,.2f}")
            print(f"  Cash Balance: ${cash:,.2f}")
            print(f"  Total Equity: ${total_value + cash:,.2f}")
            print(f"  Fund Contributions: ${fund_total:,.2f}")
        
        return None
    
    def create_unified_financial_table(self, stats_data: Dict[str, float], 
                                      summary_data: Dict[str, float]) -> None:
        """Create a unified financial overview table combining statistics and summary.
        
        Args:
            stats_data: Dictionary of portfolio statistics
            summary_data: Dictionary of financial summary data
        """
        if has_rich_support() and self.console:
            self._create_rich_unified_financial_table(stats_data, summary_data)
        else:
            self._create_plain_unified_financial_table(stats_data, summary_data)
    
    def create_financial_and_ownership_tables(self, stats_data: Dict[str, float], 
                                             summary_data: Dict[str, float],
                                             ownership_data: Dict[str, Dict[str, Any]]) -> None:
        """Create financial overview and ownership tables side by side.
        
        Args:
            stats_data: Dictionary of portfolio statistics
            summary_data: Dictionary of financial summary data
            ownership_data: Dictionary of ownership information by contributor
        """
        if has_rich_support() and self.console:
            self._create_rich_financial_and_ownership_tables(stats_data, summary_data, ownership_data)
        else:
            self._create_plain_financial_and_ownership_tables(stats_data, summary_data, ownership_data)
    
    def _create_rich_unified_financial_table(self, stats_data: Dict[str, float], 
                                            summary_data: Dict[str, float]) -> None:
        """Create Rich-formatted unified financial table."""
        
        # Create unified financial overview table
        financial_table = Table(title="💰 Financial Overview", show_header=True, header_style="bold magenta")
        financial_table.add_column("Metric", style="cyan", no_wrap=True)
        financial_table.add_column("Amount", justify="right", style="yellow")
        
        # Helper function to get color style based on value
        def get_pnl_style(value: float) -> str:
            return "green" if value >= 0 else "red"
        
        # Extract values
        total_value = summary_data.get('portfolio_value', 0)
        cash = summary_data.get('cash_balance', 0)
        total_contributions = stats_data.get('total_contributions', 0)
        cost_basis = stats_data.get('total_cost_basis', 0)
        unrealized_pnl = stats_data.get('total_pnl', 0)
        realized_pnl = stats_data.get('total_realized_pnl', 0)
        total_portfolio_pnl = stats_data.get('total_portfolio_pnl', 0)
        total_equity = total_value + cash
        
        # Portfolio Value Section
        financial_table.add_row("📊 Current Portfolio Value", f"${total_value:,.2f}")
        financial_table.add_row("💰 Cash Balance", f"${cash:,.2f}")
        financial_table.add_row("🏦 Total Equity", f"[bold]${total_equity:,.2f}[/bold]")
        
        # Add separator
        financial_table.add_row("", "")
        
        # Investment Performance Section
        financial_table.add_row("💵 Total Contributions", f"${total_contributions:,.2f}")
        financial_table.add_row("📈 Total Cost Basis", f"${cost_basis:,.2f}")
        
        # Add separator
        financial_table.add_row("", "")
        
        # P&L Section with color coding
        financial_table.add_row("💹 Unrealized P&L", f"${unrealized_pnl:,.2f}",
                               style=get_pnl_style(unrealized_pnl))
        financial_table.add_row("💰 Realized P&L", f"${realized_pnl:,.2f}",
                               style=get_pnl_style(realized_pnl))
        financial_table.add_row("📊 Total Portfolio P&L", f"[bold]${total_portfolio_pnl:,.2f}[/bold]",
                               style=get_pnl_style(total_portfolio_pnl))
        
        # Calculate and display overall performance
        if total_contributions > 0:
            overall_return_pct = (total_portfolio_pnl / total_contributions) * 100
            financial_table.add_row("📈 Overall Return", f"[bold]{overall_return_pct:+.2f}%[/bold]",
                                   style=get_pnl_style(overall_return_pct))
        
        self.console.print(financial_table)
    
    def _create_rich_financial_and_ownership_tables(self, stats_data: Dict[str, float], 
                                                   summary_data: Dict[str, float],
                                                   ownership_data: Dict[str, Dict[str, Any]]) -> None:
        """Create Rich-formatted financial and ownership tables side by side."""
        from rich.columns import Columns
        
        # Create financial overview table (reuse existing logic)
        financial_table = Table(title="💰 Financial Overview", show_header=True, header_style="bold magenta")
        financial_table.add_column("Metric", style="cyan", no_wrap=True)
        financial_table.add_column("Amount", justify="right", style="yellow")
        
        # Helper function to get color style based on value
        def get_pnl_style(value: float) -> str:
            return "green" if value >= 0 else "red"
        
        # Extract values
        total_value = summary_data.get('portfolio_value', 0)
        cash = summary_data.get('cash_balance', 0)
        total_contributions = stats_data.get('total_contributions', 0)
        cost_basis = stats_data.get('total_cost_basis', 0)
        unrealized_pnl = stats_data.get('total_pnl', 0)
        realized_pnl = stats_data.get('total_realized_pnl', 0)
        total_portfolio_pnl = stats_data.get('total_portfolio_pnl', 0)
        total_equity = total_value + cash
        
        # Portfolio Value Section
        financial_table.add_row("📊 Current Portfolio Value", f"${total_value:,.2f}")
        financial_table.add_row("💰 Cash Balance", f"${cash:,.2f}")
        financial_table.add_row("🏦 Total Equity", f"[bold]${total_equity:,.2f}[/bold]")
        
        # Add separator
        financial_table.add_row("", "")
        
        # Investment Performance Section
        financial_table.add_row("💵 Total Contributions", f"${total_contributions:,.2f}")
        financial_table.add_row("📈 Total Cost Basis", f"${cost_basis:,.2f}")
        
        # Add separator
        financial_table.add_row("", "")
        
        # P&L Section with color coding
        financial_table.add_row("💹 Unrealized P&L", f"${unrealized_pnl:,.2f}",
                               style=get_pnl_style(unrealized_pnl))
        financial_table.add_row("💰 Realized P&L", f"${realized_pnl:,.2f}",
                               style=get_pnl_style(realized_pnl))
        financial_table.add_row("📊 Total Portfolio P&L", f"[bold]${total_portfolio_pnl:,.2f}[/bold]",
                               style=get_pnl_style(total_portfolio_pnl))
        
        # Calculate and display overall performance
        if total_contributions > 0:
            overall_return_pct = (total_portfolio_pnl / total_contributions) * 100
            financial_table.add_row("📈 Overall Return", f"[bold]{overall_return_pct:+.2f}%[/bold]",
                                   style=get_pnl_style(overall_return_pct))
        
        # Create ownership table
        ownership_table = Table(title="👥 Ownership Details", show_header=True, header_style="bold blue")
        ownership_table.add_column("Contributor", style="yellow", no_wrap=True)
        ownership_table.add_column("Shares", justify="right", style="cyan")
        ownership_table.add_column("Contributed", justify="right", style="green")
        ownership_table.add_column("Ownership %", justify="right", style="magenta")
        ownership_table.add_column("Current Value", justify="right", style="red")
        
        # Sort by ownership percentage (highest first)
        sorted_ownership = sorted(ownership_data.items(), 
                                key=lambda x: x[1].get('ownership_pct', 0), reverse=True)
        
        for contributor, data in sorted_ownership:
            ownership_table.add_row(
                contributor,
                f"{data.get('shares', 0):.2f}",
                f"${data.get('contributed', 0):,.2f}",
                f"{data.get('ownership_pct', 0):.1f}%",
                f"${data.get('current_value', 0):,.2f}"
            )
        
        # Display tables side by side
        columns = Columns([financial_table, ownership_table], equal=True, expand=True)
        self.console.print(columns)
    
    def _create_plain_unified_financial_table(self, stats_data: Dict[str, float], 
                                             summary_data: Dict[str, float]) -> None:
        """Create plain text unified financial table."""
        from display.console_output import _safe_emoji
        
        # Helper function to get color based on value
        def get_pnl_color(value: float) -> str:
            return Fore.GREEN if value >= 0 else Fore.RED
        
        # Extract values
        total_value = summary_data.get('portfolio_value', 0)
        cash = summary_data.get('cash_balance', 0)
        total_contributions = stats_data.get('total_contributions', 0)
        cost_basis = stats_data.get('total_cost_basis', 0)
        unrealized_pnl = stats_data.get('total_pnl', 0)
        realized_pnl = stats_data.get('total_realized_pnl', 0)
        total_portfolio_pnl = stats_data.get('total_portfolio_pnl', 0)
        total_equity = total_value + cash
        
        print(f"\n{Fore.MAGENTA}{_safe_emoji('💰')} Financial Overview:{Style.RESET_ALL}")
        print("─" * 50)
        
        # Portfolio Value Section
        print(f"  Current Portfolio Value: ${total_value:,.2f}")
        print(f"  Cash Balance: ${cash:,.2f}")
        print(f"  {Fore.CYAN}Total Equity: ${total_equity:,.2f}{Style.RESET_ALL}")
        print()
        
        # Investment Performance Section  
        print(f"  Total Contributions: ${total_contributions:,.2f}")
        print(f"  Total Cost Basis: ${cost_basis:,.2f}")
        print()
        
        # P&L Section with color coding
        print(f"  Unrealized P&L: {get_pnl_color(unrealized_pnl)}${unrealized_pnl:,.2f}{Style.RESET_ALL}")
        print(f"  Realized P&L: {get_pnl_color(realized_pnl)}${realized_pnl:,.2f}{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}Total Portfolio P&L: {get_pnl_color(total_portfolio_pnl)}${total_portfolio_pnl:,.2f}{Style.RESET_ALL}")
        
        # Calculate and display overall performance
        if total_contributions > 0:
            overall_return_pct = (total_portfolio_pnl / total_contributions) * 100
            print(f"  {Fore.CYAN}Overall Return: {get_pnl_color(overall_return_pct)}{overall_return_pct:+.2f}%{Style.RESET_ALL}")
    
    def _create_plain_financial_and_ownership_tables(self, stats_data: Dict[str, float], 
                                                   summary_data: Dict[str, float],
                                                   ownership_data: Dict[str, Dict[str, Any]]) -> None:
        """Create plain text financial and ownership tables side by side."""
        from display.console_output import _safe_emoji
        
        # Helper function to get color based on value
        def get_pnl_color(value: float) -> str:
            return Fore.GREEN if value >= 0 else Fore.RED
        
        # Extract financial values
        total_value = summary_data.get('portfolio_value', 0)
        cash = summary_data.get('cash_balance', 0)
        total_contributions = stats_data.get('total_contributions', 0)
        cost_basis = stats_data.get('total_cost_basis', 0)
        unrealized_pnl = stats_data.get('total_pnl', 0)
        realized_pnl = stats_data.get('total_realized_pnl', 0)
        total_portfolio_pnl = stats_data.get('total_portfolio_pnl', 0)
        total_equity = total_value + cash
        
        # Prepare financial data lines
        financial_lines = [
            f"{_safe_emoji('💰')} Financial Overview",
            "─" * 35,
            f"  Current Portfolio Value: ${total_value:,.2f}",
            f"  Cash Balance: ${cash:,.2f}",
            f"  {Fore.CYAN}Total Equity: ${total_equity:,.2f}{Style.RESET_ALL}",
            "",
            f"  Total Contributions: ${total_contributions:,.2f}",
            f"  Total Cost Basis: ${cost_basis:,.2f}",
            "",
            f"  Unrealized P&L: {get_pnl_color(unrealized_pnl)}${unrealized_pnl:,.2f}{Style.RESET_ALL}",
            f"  Realized P&L: {get_pnl_color(realized_pnl)}${realized_pnl:,.2f}{Style.RESET_ALL}",
            f"  {Fore.CYAN}Total Portfolio P&L: {get_pnl_color(total_portfolio_pnl)}${total_portfolio_pnl:,.2f}{Style.RESET_ALL}"
        ]
        
        # Add overall return if contributions exist
        if total_contributions > 0:
            overall_return_pct = (total_portfolio_pnl / total_contributions) * 100
            financial_lines.append(f"  {Fore.CYAN}Overall Return: {get_pnl_color(overall_return_pct)}{overall_return_pct:+.2f}%{Style.RESET_ALL}")
        
        # Prepare ownership data lines
        ownership_lines = [
            f"{_safe_emoji('👥')} Ownership Details",
            "─" * 35,
        ]
        
        # Sort by ownership percentage (highest first)
        sorted_ownership = sorted(ownership_data.items(), 
                                key=lambda x: x[1].get('ownership_pct', 0), reverse=True)
        
        for contributor, data in sorted_ownership:
            shares = data.get('shares', 0)
            contributed = data.get('contributed', 0)
            ownership_pct = data.get('ownership_pct', 0)
            current_value = data.get('current_value', 0)
            
            # Format contributor line
            contrib_line = f"  {contributor[:15]:<15}: {shares:>6.1f} shares"
            ownership_lines.append(contrib_line)
            ownership_lines.append(f"    ${contributed:>7,.0f} ({ownership_pct:4.1f}%) = ${current_value:>8,.0f}")
        
        # Display side by side
        print("\n")
        max_lines = max(len(financial_lines), len(ownership_lines))
        for i in range(max_lines):
            financial_line = financial_lines[i] if i < len(financial_lines) else ""
            ownership_line = ownership_lines[i] if i < len(ownership_lines) else ""
            
            # Pad the financial line to consistent width
            financial_padded = f"{financial_line:<50}"
            print(f"{financial_padded} {ownership_line}")
    
    def create_trade_menu(self) -> None:
        """Create the trading menu display."""
        if has_rich_support() and self.console:
            panel = Panel(
                "[bold green]📈 Trading Menu[/bold green]\\n\\n"
                "[cyan]'b'[/cyan] 🛒 Buy (Limit Order or Market Open Order)\\n"
                "[cyan]'s'[/cyan] 📤 Sell (Limit Order)\\n"
                "[cyan]'c'[/cyan] 💵 Log Contribution\\n"
                "[cyan]'w'[/cyan] 💸 Log Withdrawal\\n"
                "[cyan]'u'[/cyan] 🔄 Update Cash Balances\\n"
                "[cyan]'sync'[/cyan] 🔗 Sync Fund Contributions\\n"
                "[cyan]'backup'[/cyan] 💾 Create Backup\\n"
                "[cyan]'restore'[/cyan] 🔄 Restore from Backup\\n"
                "[cyan]Enter[/cyan] ➤  Continue to Portfolio Processing",
                border_style="green",
                width=62
            )
            self.console.print(panel)
        else:
            from .console_output import _safe_emoji
            print(f"\\n{Fore.GREEN}{_safe_emoji('📈')} Trading Menu:{Style.RESET_ALL}")
            print(f"{Fore.CYAN}'b'{Style.RESET_ALL} {_safe_emoji('🛒')} Buy (Limit Order or Market Open Order)")
            print(f"{Fore.CYAN}'s'{Style.RESET_ALL} {_safe_emoji('📤')} Sell (Limit Order)")
            print(f"{Fore.CYAN}'c'{Style.RESET_ALL} {_safe_emoji('💵')} Log Contribution")
            print(f"{Fore.CYAN}'w'{Style.RESET_ALL} {_safe_emoji('💸')} Log Withdrawal")
            print(f"{Fore.CYAN}'u'{Style.RESET_ALL} {_safe_emoji('🔄')} Update Cash Balances")
            print(f"{Fore.CYAN}'sync'{Style.RESET_ALL} {_safe_emoji('🔗')} Sync Fund Contributions")
            print(f"{Fore.CYAN}'backup'{Style.RESET_ALL} {_safe_emoji('💾')} Create Backup")
            print(f"{Fore.CYAN}'restore'{Style.RESET_ALL} {_safe_emoji('🔄')} Restore from Backup")
            print(f"{Fore.CYAN}Enter{Style.RESET_ALL} {_safe_emoji('➤')} Continue to Portfolio Processing")


# Convenience functions for backward compatibility
def create_portfolio_table(portfolio_data: Union[List[Dict[str, Any]], 'pd.DataFrame'], 
                         data_dir: Optional[str] = None,
                         current_date: Optional[str] = None,
                         output_format: str = "display") -> Optional[str]:
    """Create a portfolio table display.
    
    Convenience function that creates a TableFormatter instance and calls create_portfolio_table.
    Supports both pandas DataFrame (original) and list of dictionaries (new) for backward compatibility.
    """
    formatter = TableFormatter(data_dir=data_dir)
    return formatter.create_portfolio_table(portfolio_data, current_date, output_format)


def create_ownership_table(ownership_data: Dict[str, Dict[str, Any]], 
                         data_dir: Optional[str] = None,
                         output_format: str = "display") -> Optional[str]:
    """Create an ownership details table.
    
    Convenience function that creates a TableFormatter instance and calls create_ownership_table.
    """
    formatter = TableFormatter(data_dir=data_dir)
    return formatter.create_ownership_table(ownership_data, output_format)


def create_statistics_table(stats_data: Dict[str, float], 
                          data_dir: Optional[str] = None,
                          output_format: str = "display") -> Optional[str]:
    """Create a portfolio statistics table.
    
    Convenience function that creates a TableFormatter instance and calls create_statistics_table.
    """
    formatter = TableFormatter(data_dir=data_dir)
    return formatter.create_statistics_table(stats_data, output_format)


def create_summary_table(summary_data: Dict[str, float], 
                       data_dir: Optional[str] = None,
                       output_format: str = "display") -> Optional[str]:
    """Create a financial summary table.
    
    Convenience function that creates a TableFormatter instance and calls create_summary_table.
    """
    formatter = TableFormatter(data_dir=data_dir)
    return formatter.create_summary_table(summary_data, output_format)


def create_unified_financial_table(stats_data: Dict[str, float], 
                                   summary_data: Dict[str, float],
                                   data_dir: Optional[str] = None) -> None:
    """Create a unified financial overview table combining statistics and summary.
    
    Convenience function that creates a TableFormatter instance and displays unified financial table.
    
    Args:
        stats_data: Dictionary of portfolio statistics
        summary_data: Dictionary of financial summary data
        data_dir: Optional data directory path for context
    """
    formatter = TableFormatter(data_dir=data_dir)
    formatter.create_unified_financial_table(stats_data, summary_data)


def create_financial_and_ownership_tables(stats_data: Dict[str, float], 
                                         summary_data: Dict[str, float],
                                         ownership_data: Dict[str, Dict[str, Any]],
                                         data_dir: Optional[str] = None) -> None:
    """Create financial overview and ownership tables side by side.
    
    Convenience function that creates a TableFormatter instance and displays side-by-side tables.
    
    Args:
        stats_data: Dictionary of portfolio statistics
        summary_data: Dictionary of financial summary data
        ownership_data: Dictionary of ownership information by contributor
        data_dir: Optional data directory path for context
    """
    formatter = TableFormatter(data_dir=data_dir)
    formatter.create_financial_and_ownership_tables(stats_data, summary_data, ownership_data)


def print_trade_menu(data_dir: Optional[str] = None) -> None:
    """Print the trading menu.
    
    Convenience function that creates a TableFormatter instance and calls create_trade_menu.
    """
    formatter = TableFormatter(data_dir=data_dir)
    formatter.create_trade_menu()


# Additional backward compatibility aliases
def create_portfolio_table_original(portfolio_df) -> None:
    """Create a portfolio table display - original function signature for backward compatibility.
    
    This function matches the exact signature from the original trading_script.py:
    def create_portfolio_table(portfolio_df: pd.DataFrame) -> None
    """
    # Just call the main function - it already handles DataFrames correctly
    create_portfolio_table(portfolio_df)