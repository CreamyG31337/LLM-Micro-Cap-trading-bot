/**
 * Congress Trades JavaScript
 * Handles AgGrid initialization and interactions
 */

let gridApi = null;
let gridColumnApi = null;

// Ticker cell renderer - makes ticker clickable
class TickerCellRenderer {
    init(params) {
        this.eGui = document.createElement('span');
        if (params.value && params.value !== 'N/A') {
            this.eGui.innerText = params.value;
            this.eGui.style.color = '#1f77b4';
            this.eGui.style.fontWeight = 'bold';
            this.eGui.style.textDecoration = 'underline';
            this.eGui.style.cursor = 'pointer';
            this.eGui.addEventListener('click', function(e) {
                e.stopPropagation();
                const ticker = params.value;
                if (ticker && ticker !== 'N/A') {
                    window.location.href = `/v2/ticker?ticker=${encodeURIComponent(ticker)}`;
                }
            });
        } else {
            this.eGui.innerText = params.value || 'N/A';
        }
    }

    getGui() {
        return this.eGui;
    }
}

// Global click handler - manages navigation vs selection
function onCellClicked(params) {
    if (params.data) {
        // Determine action based on column
        let action = 'details';
        if (params.column.colId === 'Ticker' && params.value && params.value !== 'N/A') {
            action = 'navigate';
            // Navigate immediately for ticker clicks
            const ticker = params.value;
            window.location.href = `/v2/ticker?ticker=${encodeURIComponent(ticker)}`;
            return;
        }
        
        // Update hidden column
        params.node.setDataValue('_click_action', action);
        
        // Select the row to trigger selection event
        const selectedNodes = gridApi.getSelectedNodes();
        selectedNodes.forEach(function(node) {
            node.setSelected(false);
        });
        params.node.setSelected(true);
    }
}

// Handle row selection - show AI reasoning
function onSelectionChanged() {
    const selectedRows = gridApi.getSelectedRows();
    if (selectedRows && selectedRows.length > 0) {
        const selectedRow = selectedRows[0];
        // Get full reasoning - check both _full_reasoning and _tooltip fields
        const fullReasoning = (selectedRow._full_reasoning && selectedRow._full_reasoning.trim()) || 
                             (selectedRow._tooltip && selectedRow._tooltip.trim()) || 
                             '';
        
        if (fullReasoning) {
            // Show reasoning section
            const reasoningSection = document.getElementById('ai-reasoning-section');
            if (reasoningSection) {
                reasoningSection.classList.remove('hidden');
                
                // Populate fields
                const tickerEl = document.getElementById('reasoning-ticker');
                const companyEl = document.getElementById('reasoning-company');
                const politicianEl = document.getElementById('reasoning-politician');
                const dateEl = document.getElementById('reasoning-date');
                const typeEl = document.getElementById('reasoning-type');
                const scoreEl = document.getElementById('reasoning-score');
                const textEl = document.getElementById('reasoning-text');
                
                if (tickerEl) tickerEl.textContent = selectedRow.Ticker || '-';
                if (companyEl) companyEl.textContent = selectedRow.Company || '-';
                if (politicianEl) politicianEl.textContent = selectedRow.Politician || '-';
                if (dateEl) dateEl.textContent = selectedRow.Date || '-';
                if (typeEl) typeEl.textContent = selectedRow.Type || '-';
                if (scoreEl) scoreEl.textContent = selectedRow.Score || '-';
                if (textEl) textEl.textContent = fullReasoning;
                
                // Scroll to reasoning section
                reasoningSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
    } else {
        // Hide reasoning section if no selection
        const reasoningSection = document.getElementById('ai-reasoning-section');
        if (reasoningSection) {
            reasoningSection.classList.add('hidden');
        }
    }
}

function initializeCongressTradesGrid(tradesData) {
    const gridDiv = document.querySelector('#congress-trades-grid');
    if (!gridDiv) {
        console.error('Congress trades grid container not found');
        return;
    }

    // Column definitions
    const columnDefs = [
        {
            field: 'Ticker',
            headerName: 'Ticker',
            width: 80,
            pinned: 'left',
            cellRenderer: TickerCellRenderer,
            sortable: true,
            filter: true
        },
        {
            field: 'Company',
            headerName: 'Company',
            width: 200,
            sortable: true,
            filter: true
        },
        {
            field: 'Politician',
            headerName: 'Politician',
            width: 180,
            sortable: true,
            filter: true
        },
        {
            field: 'Chamber',
            headerName: 'Chamber',
            width: 90,
            sortable: true,
            filter: true
        },
        {
            field: 'Party',
            headerName: 'Party',
            width: 80,
            sortable: true,
            filter: true
        },
        {
            field: 'State',
            headerName: 'State',
            width: 70,
            sortable: true,
            filter: true
        },
        {
            field: 'Date',
            headerName: 'Date',
            width: 110,
            sortable: true,
            filter: true
        },
        {
            field: 'Type',
            headerName: 'Type',
            width: 90,
            sortable: true,
            filter: true
        },
        {
            field: 'Amount',
            headerName: 'Amount',
            width: 120,
            sortable: true,
            filter: true
        },
        {
            field: 'Score',
            headerName: 'Score',
            width: 100,
            sortable: true,
            filter: true
        },
        {
            field: 'Owner',
            headerName: 'Owner',
            width: 100,
            sortable: true,
            filter: true
        },
        {
            field: 'AI Reasoning',
            headerName: 'AI Reasoning',
            width: 400,
            sortable: true,
            filter: true,
            tooltipValueGetter: function(params) {
                return params.data._tooltip || params.value || '';
            },
            cellStyle: {
                'white-space': 'nowrap',
                'overflow': 'hidden',
                'text-overflow': 'ellipsis'
            }
        },
        {
            field: '_tooltip',
            headerName: '_tooltip',
            hide: true
        },
        {
            field: '_click_action',
            headerName: '_click_action',
            hide: true
        },
        {
            field: '_full_reasoning',
            headerName: '_full_reasoning',
            hide: true
        }
    ];

    // Grid options
    const gridOptions = {
        columnDefs: columnDefs,
        rowData: tradesData,
        defaultColDef: {
            editable: false,
            sortable: true,
            filter: true,
            resizable: true
        },
        rowSelection: 'multiple',
        suppressRowClickSelection: true,
        enableRangeSelection: true,
        enableCellTextSelection: true,
        ensureDomOrder: true,
        domLayout: 'normal',
        pagination: true,
        paginationPageSize: 100,
        paginationPageSizeSelector: [100, 250, 500, 1000],
        onCellClicked: onCellClicked,
        onSelectionChanged: onSelectionChanged,
        animateRows: true,
        suppressCellFocus: false
    };

    // Create grid
    const gridInstance = new agGrid.Grid(gridDiv, gridOptions);
    gridApi = gridInstance.api;
    gridColumnApi = gridInstance.columnApi;
    
    // Auto-size columns on first data render
    if (gridApi) {
        gridApi.sizeColumnsToFit();
    }
}
