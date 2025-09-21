#!/usr/bin/env python3
"""
Test script to check if Rich is stripping + signs from markup.
"""

from rich.console import Console
from rich.table import Table

def test_rich_plus_signs():
    """Test if Rich preserves + signs in markup."""
    console = Console()
    
    # Test basic markup
    print("Testing basic Rich markup:")
    console.print("[green]+$150.50 +5.2%[/green]")
    console.print("[red]$75.00 -2.1%[/red]")
    
    # Test in a simple table
    print("\nTesting in Rich table:")
    table = Table(title="+ Sign Test")
    table.add_column("Test Case")
    table.add_column("Value")
    
    table.add_row("Positive with +", "[green]+$150.50 +5.2%[/green]")
    table.add_row("Negative", "[red]$75.00 -2.1%[/red]")
    table.add_row("Raw text with +", "+$100.00 +10.0%")
    
    console.print(table)
    
    # Test if the issue is with column styling
    print("\nTesting column styling effects:")
    styled_table = Table(title="Styled Column Test")
    styled_table.add_column("Normal Column")
    styled_table.add_column("Magenta Column", style="magenta")  # Same style as your Total P&L column
    
    styled_table.add_row("Test", "[green]+$150.50 +5.2%[/green]")
    styled_table.add_row("Raw", "+$100.00 +10.0%")
    
    console.print(styled_table)

if __name__ == "__main__":
    test_rich_plus_signs()