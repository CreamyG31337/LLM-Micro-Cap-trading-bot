"""
AgGrid Utilities for Enhanced DataFrames
==========================================

Provides reusable AgGrid configurations with support for:
- Ticker navigation (single-tab, in-app)
- Consistent styling
- Copy-to-clipboard
"""

import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from typing import Optional


TICKER_CELL_RENDERER_JS = """
class TickerCellRenderer {
    init(params) {
        this.eGui = document.createElement('span');
        if (params.value && params.value !== 'N/A') {
            this.eGui.innerText = params.value;
            this.eGui.style.color = '#1f77b4';
            this.eGui.style.fontWeight = 'bold';
            this.eGui.style.textDecoration = 'underline';
            this.eGui.style.cursor = 'pointer';
        } else {
            this.eGui.innerText = params.value || 'N/A';
        }
    }

    getGui() {
        return this.eGui;
    }
}
"""

TICKER_CLICK_HANDLER_JS_TEMPLATE = """
function(params) {{
    // Only handle clicks on the {col_id} column
    if (params.column && params.column.colId === '{col_id}' && params.value && params.value !== 'N/A') {{
        // Select the row to trigger navigation
        params.api.getSelectedNodes().forEach(function(node) {{
            node.setSelected(false);
        }});
        params.node.setSelected(true);
    }}
}}
"""

GLOBAL_CLICK_HANDLER_JS = """
function(params) {
    if (params.data) {
        // Determine action based on column
        var action = 'details';
        if (params.column.colId === 'Ticker' && params.value && params.value !== 'N/A') {
            action = 'navigate';
        }
        
        // Update hidden column
        params.node.setDataValue('_click_action', action);
        
        // Select the row to trigger Python callback
        // We select it AFTER setting the data value so the update is included
        params.api.getSelectedNodes().forEach(function(node) {
            node.setSelected(false);
        });
        params.node.setSelected(true);
    }
}
"""

def display_aggrid_with_ticker_navigation(
    df: pd.DataFrame,
    ticker_column: str = "Ticker",
    height: int = 400,
    enable_selection: bool = True,
    fit_columns: bool = True,
    **grid_options
) -> Optional[str]:
    """
    Display a DataFrame using AgGrid with ticker navigation support.
    
    When a row is selected, automatically navigates to the ticker details page
    in the same tab (no new window).
    
    Args:
        df: DataFrame to display
        ticker_column: Name of the column containing ticker symbols
        height: Height of the grid in pixels
        enable_selection: Whether to enable row selection
        fit_columns: Whether to auto-size columns to fit
        **grid_options: Additional AgGrid options
        
    Returns:
        Selected ticker symbol if a row was clicked, None otherwise
        
    Example:
        >>> df = pd.DataFrame({'Ticker': ['AAPL', 'TSLA'], 'Price': [150, 200]})
        >>> selected = display_aggrid_with_ticker_navigation(df)
        >>> if selected:
        >>>     st.query_params["ticker"] = selected
        >>>     st.switch_page("pages/ticker_details.py")
    """
    if df.empty:
        st.info("No data to display")
        return None
    
    # Build grid options
    gb = GridOptionsBuilder.from_dataframe(df)
    
    # Enable selection
    if enable_selection:
        gb.configure_selection(
            selection_mode="single",
            use_checkbox=False,
            pre_selected_rows=[]
        )
    
    # Configure ticker column with clickable cell renderer
    if ticker_column in df.columns:
        gb.configure_column(
            ticker_column,
            header_name=ticker_column,
            cellRenderer=JsCode(TICKER_CELL_RENDERER_JS)
        )
    
    # Auto-size columns
    if fit_columns:
        gb.configure_grid_options(domLayout='normal')
    
    # Build grid options
    grid_options_dict = gb.build()
    
    # Add cell click handler for ticker column navigation
    if ticker_column in df.columns:
        grid_options_dict['onCellClicked'] = {
            'function': TICKER_CLICK_HANDLER_JS_TEMPLATE.format(col_id=ticker_column)
        }
    
    # Display grid
    grid_response = AgGrid(
        df,
        gridOptions=grid_options_dict,
        height=height,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=fit_columns,
        allow_unsafe_jscode=True,
        theme='streamlit',
        **grid_options
    )
    
    # Check if a row was selected
    try:
        selected_rows = grid_response.get('selected_rows')
        
        if selected_rows is not None and len(selected_rows) > 0:
            # AgGrid can return selected_rows as either DataFrame or list of dicts
            if isinstance(selected_rows, pd.DataFrame):
                # DataFrame format
                if ticker_column in selected_rows.columns:
                    ticker_value = str(selected_rows.iloc[0][ticker_column])
                    return ticker_value
            else:
                # List of dicts format
                selected_row = selected_rows[0]
                if isinstance(selected_row, dict) and ticker_column in selected_row:
                    ticker_value = str(selected_row[ticker_column])
                    return ticker_value
                elif hasattr(selected_row, ticker_column):
                    # Handle if it's an object with attributes
                    ticker_value = str(getattr(selected_row, ticker_column))
                    return ticker_value
        
        return None
    except Exception as e:
        st.error(f"❌ Error processing ticker selection: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None


def display_aggrid_simple(
    df: pd.DataFrame,
    height: int = 400,
    fit_columns: bool = True,
    enable_pagination: bool = False,
    **grid_options
):
    """
    Display a simple AgGrid without special navigation features.
    
    Args:
        df: DataFrame to display
        height: Height of the grid in pixels
        fit_columns: Whether to auto-size columns
        enable_pagination: Whether to enable pagination
        **grid_options: Additional AgGrid options
    """
    if df.empty:
        st.info("No data to display")
        return
    
    gb = GridOptionsBuilder.from_dataframe(df)
    
    if enable_pagination:
        gb.configure_pagination(paginationPageSize=20)
    
    if fit_columns:
        gb.configure_grid_options(domLayout='normal')
    
    grid_options_dict = gb.build()
    
    AgGrid(
        df,
        gridOptions=grid_options_dict,
        height=height,
        fit_columns_on_grid_load=fit_columns,
        theme='streamlit',
        **grid_options
    )
