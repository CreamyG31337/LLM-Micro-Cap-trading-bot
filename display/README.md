# Display Module

The display module handles all user interface and output formatting for the trading system. It provides Rich table formatting with fallback to plain text, colored console output, and terminal utilities.

## Structure

```
display/
├── table_formatter.py  # Rich table formatting and portfolio display
├── console_output.py   # Colored console output and messaging
├── terminal_utils.py   # Terminal detection, sizing, and environment handling
└── README.md          # This file
```

## Table Formatter (`table_formatter.py`)

Provides sophisticated table formatting with Rich tables and fallback support:

### Key Features
- **Rich Table Support**: Beautiful formatted tables with colors and styling
- **Plain Text Fallback**: Automatic fallback when Rich is not available
- **JSON Output**: API-ready JSON output for web dashboard integration
- **Responsive Design**: Adapts to terminal width and capabilities

### Table Types
- **Portfolio Tables**: Complete portfolio overview with positions
- **Trade History**: Formatted trade logs with filtering
- **Performance Summary**: P&L and performance metrics
- **Market Data**: Price and market information display

### Portfolio Table Layout
The portfolio snapshot table is optimized for standard display environments:

- **Target Resolution**: 1920x1080 with 125% scaling (Windows 11)
- **Terminal Width**: ~157 characters for optimal readability
- **Responsive Design**: Adapts to different terminal sizes and capabilities
- **Column Optimization**: Daily P&L and Stop Loss columns balanced for readability
- **Rich Formatting**: Beautiful tables with color coding and styling

### Usage Example
```python
from display.table_formatter import TableFormatter

formatter = TableFormatter()

# Create portfolio table
table = formatter.create_portfolio_table(portfolio_data)
formatter.display_table(table)

# Export to JSON for web API
json_data = formatter.to_json(portfolio_data)
```

### Rich Features
When Rich is available, tables include:
- Color-coded P&L (green for gains, red for losses)
- Progress bars for position weights
- Styled headers and borders
- Responsive column sizing
- Interactive elements (future)

### Fallback Mode
When Rich is unavailable:
- Clean ASCII table formatting
- Colorama-based coloring where available
- Maintains data integrity and readability
- Graceful degradation of visual features

## Console Output (`console_output.py`)

Manages colored console output and messaging throughout the system:

### Key Features
- **Colored Output**: Success, error, warning, and info messages
- **Rich Integration**: Uses Rich console when available
- **Fallback Support**: Colorama fallback for basic coloring
- **Logging Integration**: Integrates with Python logging system

### Message Types
- `print_success()`: Green success messages
- `print_error()`: Red error messages  
- `print_warning()`: Yellow warning messages
- `print_info()`: Blue informational messages
- `print_header()`: Styled section headers

### Usage Example
```python
from display.console_output import print_success, print_error, print_info

print_success("Portfolio updated successfully!")
print_error("Failed to fetch market data")
print_info("Loading portfolio data...")
```

### Rich Console Features
- Emoji support for visual indicators
- Progress bars for long operations
- Styled text with markup support
- Panel displays for important information

## Terminal Utils (`terminal_utils.py`)

Provides terminal detection, sizing, and environment handling:

### Key Features
- **Terminal Detection**: Identify terminal type and capabilities
- **Width Detection**: Automatic terminal width detection
- **Environment Detection**: OS and shell environment identification
- **Display Optimization**: Optimize display for different environments

### Detection Capabilities
- **Terminal Width**: Automatic width detection with fallbacks
- **Color Support**: Detect terminal color capabilities
- **Rich Support**: Determine if Rich features are available
- **Test Environment**: Detect test/CI environments

### Usage Example
```python
from display.terminal_utils import get_optimal_table_width, detect_environment

# Get optimal table width
width = get_optimal_table_width()

# Detect environment
env_info = detect_environment()
print(f"Running in {env_info['os']} with {env_info['terminal']}")
```

### Environment Handling
- **Windows**: Proper Windows console handling
- **Linux/macOS**: Unix terminal optimization
- **CI/CD**: Special handling for automated environments
- **Docker**: Container environment detection

## Design Principles

### Progressive Enhancement
The display module follows progressive enhancement principles:
1. **Base Functionality**: Plain text output always works
2. **Enhanced Features**: Rich formatting when available
3. **Graceful Degradation**: Fallback to simpler formats when needed

### Repository Independence
Display functions work with data from any repository:
- Accept data models as parameters
- No direct data access or file operations
- Pure presentation layer separation

### Accessibility
- High contrast color schemes
- Screen reader compatible output
- Keyboard navigation support (future)
- Customizable display preferences

## Configuration

Display behavior can be configured through settings:

```json
{
  "display": {
    "use_rich": true,
    "use_colors": true,
    "table_style": "default",
    "max_table_width": 120,
    "currency_display": "symbol",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "number_format": {
      "decimal_places": 2,
      "thousands_separator": ","
    }
  }
}
```

## Web Dashboard Integration

The display module is designed for future web dashboard integration:

### JSON Output
All formatters support JSON serialization:
```python
# Portfolio data as JSON for web API
json_data = formatter.portfolio_to_json(portfolio)

# Market data as JSON
market_json = formatter.market_data_to_json(market_data)
```

### API-Ready Formatting
- Structured data output for REST APIs
- Consistent formatting across all data types
- Metadata inclusion for client-side rendering

## Testing

Comprehensive testing ensures display reliability:

### Visual Testing
- Output format validation
- Color scheme testing
- Table layout verification
- Responsive design testing

### Environment Testing
- Multiple terminal types
- Different operating systems
- Various screen sizes
- Accessibility compliance

### Fallback Testing
- Rich unavailable scenarios
- Limited color support
- Narrow terminal widths
- CI/CD environment compatibility

## Performance Considerations

### Efficient Rendering
- Lazy loading of large datasets
- Streaming output for real-time updates
- Memory-efficient table generation
- Caching of formatted output

### Terminal Optimization
- Minimal terminal writes
- Efficient color code usage
- Optimized table sizing
- Reduced flicker during updates

## Future Enhancements

Planned improvements for web dashboard:

### Interactive Features
- **Clickable Tables**: Interactive table elements
- **Sorting/Filtering**: Client-side data manipulation
- **Real-time Updates**: Live data streaming
- **Responsive Design**: Mobile-optimized layouts

### Advanced Visualization
- **Charts and Graphs**: Integration with plotting libraries
- **Dashboard Widgets**: Modular display components
- **Custom Themes**: User-customizable appearance
- **Export Options**: PDF, Excel, and image export

### Accessibility Improvements
- **Screen Reader Support**: Enhanced accessibility
- **Keyboard Navigation**: Full keyboard control
- **High Contrast Modes**: Accessibility-focused themes
- **Font Size Controls**: User-adjustable text sizing