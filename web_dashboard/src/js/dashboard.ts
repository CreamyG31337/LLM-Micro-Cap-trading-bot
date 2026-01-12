/**
 * Dashboard V2 - Matches dashboard.html template
 * Uses /api/dashboard/* endpoints
 * 
 * ⚠️ IMPORTANT: This is a TypeScript SOURCE file.
 * - Edit this file: web_dashboard/src/js/dashboard.ts
 * - Compiled output: web_dashboard/static/js/dashboard.js (auto-generated)
 * - DO NOT edit the compiled .js file - it will be overwritten on build
 * - Run `npm run build:ts` to compile changes
 * 
 * See web_dashboard/src/js/README.md for development guidelines.
 */

// Make this a module
export { };

// Global types are declared in globals.d.ts

console.log('[Dashboard] dashboard.ts file loaded and executing...');

// Type definitions
interface DashboardSummary {
    total_value: number;
    cash_balance: number;
    day_change: number;
    day_change_pct: number;
    unrealized_pnl: number;
    unrealized_pnl_pct: number;
    display_currency: string;
    thesis?: {
        title: string;
        overview: string;
    };
    from_cache: boolean;
    processing_time: number;
}

interface PerformanceChartData {
    data: any[]; // Plotly trace data
    layout: any; // Plotly layout
}

interface AllocationChartData {
    sector?: Array<{
        label: string;
        value: number;
    }>;
    asset_class?: Array<{
        label: string;
        value: number;
    }>;
}

interface HoldingsData {
    data: Array<{
        ticker: string;
        name: string;
        sector: string;
        quantity: number;
        price: number;
        value: number;
        day_change: number;
        day_change_pct: number;
        total_return: number;
        total_return_pct: number;
    }>;
}

interface ActivityData {
    data: Array<{
        date: string;
        ticker: string;
        action: 'BUY' | 'SELL';
        shares: number;
        price: number;
        amount: number;
    }>;
}

interface Fund {
    name: string;
}

// Global state
const state = {
    currentFund: typeof window !== 'undefined' && window.INITIAL_FUND ? window.INITIAL_FUND : '',
    timeRange: 'ALL' as '1M' | '3M' | '6M' | '1Y' | 'ALL',
    charts: {} as Record<string, ApexChartsInstance>, // Sector chart still uses ApexCharts
    gridApi: null as any // AG Grid API
};

// Initialize
document.addEventListener('DOMContentLoaded', (): void => {
    console.log('[Dashboard] DOMContentLoaded event fired, initializing dashboard...');

    // Init components
    initTimeDisplay();
    initFundSelector();
    initTimeRangeControls();
    initGrid(); // Initialize empty grid

    // Fetch Data
    refreshDashboard();

    // Auto-refresh every 60s (optional)
    // setInterval(refreshDashboard, 60000);
});

// --- Initialization Functions ---

function initTimeDisplay(): void {
    const el = document.getElementById('last-updated-text');
    if (el) {
        el.textContent = 'Last updated: ' + new Date().toLocaleString();
    }
}

async function initFundSelector(): Promise<void> {
    const selector = document.getElementById('global-fund-select') as HTMLSelectElement | null;
    console.log('[Dashboard] Initializing navigation fund selector...', {
        found: !!selector,
        current_state_fund: state.currentFund
    });

    if (!selector) {
        console.warn('[Dashboard] Global fund selector not found in sidebar!');
        return;
    }

    // Set initial state from selector if not already set
    if (!state.currentFund) {
        state.currentFund = selector.value;
        console.log('[Dashboard] Initial state set from selector value:', state.currentFund);
    } else {
        // Sync selector with state (e.g. if set from INITIAL_FUND)
        if (selector.value !== state.currentFund) {
            console.log('[Dashboard] Syncing selector value to state:', state.currentFund);
            selector.value = state.currentFund;
        }
    }

    // Listen for changes
    selector.addEventListener('change', (e: Event): void => {
        const target = e.target as HTMLSelectElement;
        state.currentFund = target.value;
        console.log('[Dashboard] Global fund changed to:', state.currentFund);
        refreshDashboard();
    });
}

function initTimeRangeControls(): void {
    document.querySelectorAll('.range-btn').forEach(btn => {
        btn.addEventListener('click', (e: Event): void => {
            const target = e.target as HTMLElement;

            // Update UI
            document.querySelectorAll('.range-btn').forEach(b => {
                b.classList.remove('active', 'ring-2', 'ring-blue-700', 'text-blue-700', 'z-10');
                b.classList.add('text-gray-900', 'hover:text-blue-700', 'dark:text-white');
            });
            target.classList.add('active', 'ring-2', 'ring-blue-700', 'text-blue-700', 'z-10');

            // Update State
            const range = target.dataset.range as '1M' | '3M' | '6M' | '1Y' | 'ALL';
            if (range) {
                state.timeRange = range;
                console.log('[Dashboard] Time range changed to:', state.timeRange);

                // Refresh Charts only
                fetchPerformanceChart();
            }
        });
    });
}

function initGrid(): void {
    console.log('[Dashboard] Initializing AG Grid...');
    const gridEl = document.getElementById('holdings-grid');
    if (!gridEl) {
        console.warn('[Dashboard] Holdings grid element not found');
        return;
    }

    const columnDefs = [
        { field: 'ticker', headerName: 'Ticker', width: 100, pinned: 'left' },
        { field: 'name', headerName: 'Company', width: 200 },
        { field: 'sector', headerName: 'Sector', width: 150 },
        { field: 'quantity', headerName: 'Shares', width: 100, type: 'numericColumn' },
        { field: 'price', headerName: 'Price', width: 100, type: 'numericColumn', valueFormatter: (params: any) => formatMoney(params.value) },
        { field: 'value', headerName: 'Value', width: 120, type: 'numericColumn', valueFormatter: (params: any) => formatMoney(params.value) },
        { field: 'day_change', headerName: 'Day Change', width: 120, type: 'numericColumn', valueFormatter: (params: any) => formatMoney(params.value) },
        { field: 'day_change_pct', headerName: 'Day %', width: 100, type: 'numericColumn', valueFormatter: (params: any) => (params.value || 0).toFixed(2) + '%' },
        { field: 'total_return', headerName: 'Total Return', width: 120, type: 'numericColumn', valueFormatter: (params: any) => formatMoney(params.value) },
        { field: 'total_return_pct', headerName: 'Total %', width: 100, type: 'numericColumn', valueFormatter: (params: any) => (params.value || 0).toFixed(2) + '%' }
    ];

    const gridOptions = {
        columnDefs: columnDefs,
        defaultColDef: {
            sortable: true,
            filter: true,
            resizable: true
        },
        rowData: [],
        animateRows: true
    };

    // agGrid is loaded from CDN and available globally
    if (typeof (window as any).agGrid === 'undefined') {
        console.error('[Dashboard] AG Grid not loaded');
        return;
    }

    const agGrid = (window as any).agGrid;

    // Debug: Log what's available in agGrid
    console.log('[Dashboard] AG Grid object check:', {
        agGrid_available: !!agGrid,
        agGrid_type: typeof agGrid,
        has_createGrid: typeof agGrid.createGrid === 'function',
        has_Grid: typeof agGrid.Grid !== 'undefined',
        agGrid_keys: agGrid ? Object.keys(agGrid).slice(0, 20) : []
    });

    // AG Grid v31+ recommends createGrid() which returns the API directly
    // Check for createGrid first (v31+)
    if (typeof agGrid.createGrid === 'function') {
        console.log('[Dashboard] createGrid() is available, attempting to use it...');
        try {
            const gridApi = agGrid.createGrid(gridEl, gridOptions);
            if (gridApi && typeof gridApi.setRowData === 'function') {
                state.gridApi = gridApi;
                console.log('[Dashboard] AG Grid initialized with createGrid()', {
                    has_api: !!state.gridApi,
                    has_setRowData: typeof state.gridApi.setRowData === 'function',
                    gridApi_type: typeof state.gridApi,
                    gridApi_keys: state.gridApi ? Object.keys(state.gridApi).slice(0, 10) : []
                });
                return; // Success, exit early
            } else {
                console.error('[Dashboard] createGrid() returned invalid API:', {
                    gridApi,
                    has_setRowData: gridApi && typeof gridApi.setRowData === 'function'
                });
            }
        } catch (createError) {
            console.error('[Dashboard] Error creating grid with createGrid():', createError);
        }
    }

    // Fallback to deprecated new Grid() constructor (v30 and earlier)
    // This is the pattern used in congress_trades.ts which works
    if (agGrid.Grid) {
        console.log('[Dashboard] createGrid() not available or failed, falling back to new Grid()...');
        try {
            const gridInstance = new agGrid.Grid(gridEl, gridOptions);
            console.log('[Dashboard] Grid instance created:', {
                gridInstance,
                has_api: !!gridInstance.api,
                api_type: typeof gridInstance.api,
                api_keys: gridInstance.api ? Object.keys(gridInstance.api).slice(0, 10) : []
            });

            // In v30, the API is on gridInstance.api
            // In v31, createGrid returns the API directly
            if (gridInstance && gridInstance.api) {
                state.gridApi = gridInstance.api;
                console.log('[Dashboard] AG Grid initialized with new Grid() (deprecated)', {
                    has_api: !!state.gridApi,
                    has_setRowData: typeof state.gridApi.setRowData === 'function',
                    warning: 'Using deprecated new Grid() - consider upgrading to createGrid()'
                });
            } else {
                // Try waiting a bit for the API to be available (sometimes it's set asynchronously)
                setTimeout(() => {
                    if (gridInstance && gridInstance.api) {
                        state.gridApi = gridInstance.api;
                        console.log('[Dashboard] Grid API available after delay:', {
                            has_api: !!state.gridApi,
                            has_setRowData: typeof state.gridApi.setRowData === 'function'
                        });
                    } else {
                        console.error('[Dashboard] Grid instance created but API still not available after delay:', {
                            gridInstance,
                            has_api: gridInstance && !!gridInstance.api,
                            gridInstance_keys: gridInstance ? Object.keys(gridInstance) : []
                        });
                    }
                }, 100);
            }
        } catch (gridError) {
            console.error('[Dashboard] Error creating grid with new Grid():', gridError);
        }
    } else {
        console.error('[Dashboard] AG Grid API not found', {
            agGrid_available: typeof agGrid !== 'undefined',
            agGrid_keys: agGrid ? Object.keys(agGrid) : [],
            has_createGrid: typeof agGrid.createGrid === 'function',
            has_Grid: typeof agGrid.Grid !== 'undefined'
        });
    }
}

async function refreshDashboard(): Promise<void> {
    console.log('[Dashboard] Starting dashboard refresh...', {
        fund: state.currentFund,
        timeRange: state.timeRange,
        timestamp: new Date().toISOString()
    });

    // Hide any previous errors
    const errorContainer = document.getElementById('dashboard-error-container');
    if (errorContainer) {
        errorContainer.classList.add('hidden');
    }

    const startTime = performance.now();

    try {
        await Promise.all([
            fetchSummary(),
            fetchPerformanceChart(),
            fetchSectorChart(),
            fetchHoldings(),
            fetchActivity()
        ]);

        const duration = performance.now() - startTime;
        console.log('[Dashboard] Dashboard refresh completed successfully', {
            duration: `${duration.toFixed(2)}ms`,
            timestamp: new Date().toISOString()
        });

        // Update Time
        initTimeDisplay();
    } catch (error) {
        const duration = performance.now() - startTime;
        console.error('[Dashboard] Error refreshing dashboard:', {
            error: error,
            message: error instanceof Error ? error.message : String(error),
            stack: error instanceof Error ? error.stack : undefined,
            duration: `${duration.toFixed(2)}ms`,
            timestamp: new Date().toISOString()
        });
        showDashboardError(error);
    }
}

function showDashboardError(error: unknown): void {
    const errorContainer = document.getElementById('dashboard-error-container');
    const errorMessage = document.getElementById('dashboard-error-message');

    if (errorContainer && errorMessage) {
        const errorText = error instanceof Error ? error.message : String(error);
        const errorStack = error instanceof Error && error.stack ? `<pre class="mt-2 text-xs overflow-auto">${error.stack}</pre>` : '';

        errorMessage.innerHTML = `<p>${errorText}</p>${errorStack}`;
        errorContainer.classList.remove('hidden');
    }
}

// --- Data Fetching ---

async function fetchSummary(): Promise<void> {
    const url = `/api/dashboard/summary?fund=${encodeURIComponent(state.currentFund)}`;
    const startTime = performance.now();

    console.log('[Dashboard] Fetching summary...', { url, fund: state.currentFund });

    try {
        const response = await fetch(url, { credentials: 'include' });
        const duration = performance.now() - startTime;

        console.log('[Dashboard] Summary response received', {
            status: response.status,
            statusText: response.statusText,
            ok: response.ok,
            duration: `${duration.toFixed(2)}ms`,
            url: url
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}: ${response.statusText}` }));
            console.error('[Dashboard] Summary API error:', {
                status: response.status,
                errorData: errorData,
                url: url
            });
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data: DashboardSummary = await response.json();
        console.log('[Dashboard] Summary data received', {
            total_value: data.total_value,
            cash_balance: data.cash_balance,
            day_change: data.day_change,
            unrealized_pnl: data.unrealized_pnl,
            display_currency: data.display_currency,
            has_thesis: !!data.thesis,
            processing_time: data.processing_time,
            from_cache: data.from_cache
        });

        // Update Metrics
        updateMetric('metric-total-value', data.total_value, data.display_currency, true);
        updateMetric('metric-cash', data.cash_balance, data.display_currency, true);

        updateChangeMetric('metric-day-change', 'metric-day-pct', data.day_change, data.day_change_pct, data.display_currency);
        updateChangeMetric('metric-total-pnl', 'metric-total-pnl-pct', data.unrealized_pnl, data.unrealized_pnl_pct, data.display_currency);

        const currencyEl = document.getElementById('metric-currency');
        if (currencyEl) {
            currencyEl.textContent = data.display_currency;
        }

        // Update Thesis
        const thesisContainer = document.getElementById('thesis-container');
        if (data.thesis && data.thesis.title) {
            if (thesisContainer) {
                thesisContainer.classList.remove('hidden');
            }
            const titleEl = document.getElementById('thesis-title');
            const contentEl = document.getElementById('thesis-content');
            if (titleEl) titleEl.textContent = data.thesis.title;
            if (contentEl) {
                // Use marked.js if available, otherwise plain text
                if (typeof (window as any).marked !== 'undefined') {
                    contentEl.innerHTML = (window as any).marked.parse(data.thesis.overview || '');
                } else {
                    contentEl.textContent = data.thesis.overview || '';
                }
            }
        } else {
            if (thesisContainer) {
                thesisContainer.classList.add('hidden');
            }
        }

    } catch (error) {
        const duration = performance.now() - startTime;
        console.error('[Dashboard] Error fetching summary:', {
            error: error,
            message: error instanceof Error ? error.message : String(error),
            stack: error instanceof Error ? error.stack : undefined,
            url: url,
            fund: state.currentFund,
            duration: `${duration.toFixed(2)}ms`,
            timestamp: new Date().toISOString()
        });

        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        // Show error in metrics
        const totalValueEl = document.getElementById('metric-total-value');
        const dayChangeEl = document.getElementById('metric-day-change');
        const totalPnlEl = document.getElementById('metric-total-pnl');
        const cashEl = document.getElementById('metric-cash');

        if (totalValueEl) totalValueEl.textContent = 'Error';
        if (dayChangeEl) dayChangeEl.textContent = 'Error';
        if (totalPnlEl) totalPnlEl.textContent = 'Error';
        if (cashEl) cashEl.textContent = 'Error';

        // Show error in UI
        showDashboardError(new Error(`Failed to load summary: ${errorMsg}`));
        throw error; // Re-throw so refreshDashboard can catch it
    }
}

async function fetchPerformanceChart(): Promise<void> {
    // Detect actual theme from page (same as ticker_details.ts)
    const htmlElement = document.documentElement;
    const dataTheme = htmlElement.getAttribute('data-theme') || 'system';
    let theme: string = 'light'; // default

    if (dataTheme === 'dark') {
        theme = 'dark';
    } else if (dataTheme === 'light') {
        theme = 'light';
    } else if (dataTheme === 'system') {
        // For 'system', check if page is actually in dark mode via CSS
        const bodyBg = window.getComputedStyle(document.body).backgroundColor;
        // Check for dark mode background colors
        const isDark = bodyBg && (
            bodyBg.includes('rgb(31, 41, 55)') ||  // --bg-primary dark
            bodyBg.includes('rgb(17, 24, 39)') ||  // --bg-secondary dark  
            bodyBg.includes('rgb(55, 65, 81)')     // --bg-tertiary dark
        );
        theme = isDark ? 'dark' : 'light';
    }

    const url = `/api/dashboard/charts/performance?fund=${encodeURIComponent(state.currentFund)}&range=${state.timeRange}&theme=${encodeURIComponent(theme)}`;
    const startTime = performance.now();

    console.log('[Dashboard] Fetching performance chart...', { url, fund: state.currentFund, range: state.timeRange, theme });

    try {
        const response = await fetch(url, { credentials: 'include' });
        const duration = performance.now() - startTime;

        console.log('[Dashboard] Performance chart response received', {
            status: response.status,
            ok: response.ok,
            duration: `${duration.toFixed(2)}ms`
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}: ${response.statusText}` }));
            const errorMsg = errorData.error || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
            console.error('[Dashboard] Performance chart API error:', {
                status: response.status,
                statusText: response.statusText,
                error: errorMsg,
                errorData: JSON.stringify(errorData),
                url: url
            });
            throw new Error(errorMsg);
        }

        const data: PerformanceChartData = await response.json();
        console.log('[Dashboard] Performance chart data received', {
            has_data: !!data.data,
            has_layout: !!data.layout,
            trace_count: data.data ? data.data.length : 0
        });

        renderPerformanceChart(data);

    } catch (error) {
        const duration = performance.now() - startTime;
        const errorMsg = error instanceof Error ? error.message : String(error);
        const errorStack = error instanceof Error ? error.stack : undefined;
        console.error('[Dashboard] Error fetching performance chart:', {
            error: errorMsg,
            stack: errorStack,
            url: url,
            duration: `${duration.toFixed(2)}ms`,
            errorObject: JSON.stringify(error, Object.getOwnPropertyNames(error))
        });
        const chartEl = document.getElementById('performance-chart');
        if (chartEl) {
            chartEl.innerHTML = `<div class="text-center text-red-500 py-8"><p>Error loading chart: ${errorMsg}</p></div>`;
        }
    }
}

async function fetchSectorChart(): Promise<void> {
    const url = `/api/dashboard/charts/allocation?fund=${encodeURIComponent(state.currentFund)}`;
    const startTime = performance.now();

    console.log('[Dashboard] Fetching sector chart...', { url, fund: state.currentFund });

    try {
        const response = await fetch(url, { credentials: 'include' });
        const duration = performance.now() - startTime;

        console.log('[Dashboard] Sector chart response received', {
            status: response.status,
            ok: response.ok,
            duration: `${duration.toFixed(2)}ms`
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}: ${response.statusText}` }));
            console.error('[Dashboard] Sector chart API error:', {
                status: response.status,
                errorData: errorData,
                url: url
            });
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data: AllocationChartData = await response.json();
        console.log('[Dashboard] Sector chart data received', {
            has_sector: !!data.sector,
            has_asset_class: !!data.asset_class,
            sector_count: data.sector ? data.sector.length : 0
        });

        renderSectorChart(data);

    } catch (error) {
        const duration = performance.now() - startTime;
        console.error('[Dashboard] Error fetching sector chart:', {
            error: error,
            message: error instanceof Error ? error.message : String(error),
            url: url,
            duration: `${duration.toFixed(2)}ms`
        });
        const chartEl = document.getElementById('sector-chart');
        if (chartEl) {
            chartEl.innerHTML = `<div class="text-center text-red-500 py-8"><p>Error loading sector chart: ${error instanceof Error ? error.message : 'Unknown error'}</p></div>`;
        }
    }
}

async function fetchHoldings(): Promise<void> {
    const url = `/api/dashboard/holdings?fund=${encodeURIComponent(state.currentFund)}`;
    const startTime = performance.now();

    console.log('[Dashboard] Fetching holdings...', { url, fund: state.currentFund });

    try {
        const response = await fetch(url, { credentials: 'include' });
        const duration = performance.now() - startTime;

        console.log('[Dashboard] Holdings response received', {
            status: response.status,
            ok: response.ok,
            duration: `${duration.toFixed(2)}ms`
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}: ${response.statusText}` }));
            const errorMsg = errorData.error || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
            console.error('[Dashboard] Holdings API error:', {
                status: response.status,
                statusText: response.statusText,
                error: errorMsg,
                errorData: JSON.stringify(errorData),
                url: url
            });
            throw new Error(errorMsg);
        }

        const data: HoldingsData = await response.json();
        const rowCount = data.data ? data.data.length : 0;
        console.log('[Dashboard] Holdings data received', {
            row_count: rowCount,
            has_grid_api: !!state.gridApi
        });

        if (state.gridApi && typeof state.gridApi.setRowData === 'function') {
            state.gridApi.setRowData(data.data || []);
            console.log('[Dashboard] Holdings grid updated with', rowCount, 'rows');
        } else {
            console.error('[Dashboard] Grid API not available for updating holdings', {
                has_gridApi: !!state.gridApi,
                gridApi_type: typeof state.gridApi,
                has_setRowData: state.gridApi && typeof state.gridApi.setRowData === 'function',
                gridApi_keys: state.gridApi ? Object.keys(state.gridApi).slice(0, 10) : []
            });
            // Try to reinitialize the grid
            console.log('[Dashboard] Attempting to reinitialize grid...');
            initGrid();
            // Try again after a short delay
            setTimeout(() => {
                if (state.gridApi && typeof state.gridApi.setRowData === 'function') {
                    state.gridApi.setRowData(data.data || []);
                    console.log('[Dashboard] Holdings grid updated after reinitialization');
                }
            }, 100);
        }

    } catch (error) {
        const duration = performance.now() - startTime;
        const errorMsg = error instanceof Error ? error.message : String(error);
        const errorStack = error instanceof Error ? error.stack : undefined;
        console.error('[Dashboard] Error fetching holdings:', {
            error: errorMsg,
            stack: errorStack,
            url: url,
            duration: `${duration.toFixed(2)}ms`,
            errorObject: JSON.stringify(error, Object.getOwnPropertyNames(error))
        });
        const gridEl = document.getElementById('holdings-grid');
        if (gridEl) {
            gridEl.innerHTML = `<div class="text-center text-red-500 py-8"><p>Error loading holdings: ${errorMsg}</p></div>`;
        }
    }
}

async function fetchActivity(): Promise<void> {
    const url = `/api/dashboard/activity?fund=${encodeURIComponent(state.currentFund)}&limit=10`;
    const startTime = performance.now();

    console.log('[Dashboard] Fetching activity...', { url, fund: state.currentFund });

    try {
        const response = await fetch(url, { credentials: 'include' });
        const duration = performance.now() - startTime;

        console.log('[Dashboard] Activity response received', {
            status: response.status,
            ok: response.ok,
            duration: `${duration.toFixed(2)}ms`
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}: ${response.statusText}` }));
            console.error('[Dashboard] Activity API error:', {
                status: response.status,
                errorData: errorData,
                url: url
            });
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        const data: ActivityData = await response.json();
        const activityCount = data.data ? data.data.length : 0;
        console.log('[Dashboard] Activity data received', {
            activity_count: activityCount
        });

        const tbody = document.getElementById('activity-table-body');
        if (!tbody) {
            console.warn('[Dashboard] Activity table body not found');
            return;
        }

        tbody.innerHTML = '';

        if (!data.data || data.data.length === 0) {
            tbody.innerHTML = '<tr class="bg-white border-b dark:bg-gray-800 dark:border-gray-700"><td colspan="6" class="px-6 py-4 text-center text-gray-500">No recent activity</td></tr>';
        } else {
            data.data.forEach(row => {
                const tr = document.createElement('tr');
                tr.className = 'bg-white border-b dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600';

                const isBuy = row.action === 'BUY';
                const actionBadge = isBuy
                    ? '<span class="bg-green-100 text-green-800 text-xs font-medium px-2.5 py-0.5 rounded dark:bg-green-900 dark:text-green-300">BUY</span>'
                    : '<span class="bg-red-100 text-red-800 text-xs font-medium px-2.5 py-0.5 rounded dark:bg-red-900 dark:text-red-300">SELL</span>';

                tr.innerHTML = `
                     <td class="px-6 py-4 whitespace-nowrap">${row.date}</td>
                     <td class="px-6 py-4 font-bold text-blue-600 dark:text-blue-400">
                         <a href="/v2/ticker?ticker=${row.ticker}" class="hover:underline">${row.ticker}</a>
                     </td>
                     <td class="px-6 py-4">${actionBadge}</td>
                     <td class="px-6 py-4 text-right">${row.shares}</td>
                     <td class="px-6 py-4 text-right format-currency">${formatMoney(row.price)}</td>
                     <td class="px-6 py-4 text-right format-currency font-medium">${formatMoney(row.amount || (row.shares * row.price))}</td>
                `;
                tbody.appendChild(tr);
            });
        }

    } catch (error) {
        const duration = performance.now() - startTime;
        console.error('[Dashboard] Error fetching activity:', {
            error: error,
            message: error instanceof Error ? error.message : String(error),
            url: url,
            duration: `${duration.toFixed(2)}ms`
        });
        const tableBody = document.getElementById('activity-table-body');
        if (tableBody) {
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-red-500 py-4">Error loading activity: ${error instanceof Error ? error.message : 'Unknown error'}</td></tr>`;
        }
    }
}

// --- Rendering Helpers ---

function formatMoney(val: number, currency?: string): string {
    if (typeof val !== 'number' || isNaN(val)) return '--';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: currency || 'USD' }).format(val);
}

function updateMetric(id: string, value: number, currency: string, isCurrency: boolean): void {
    const el = document.getElementById(id);
    if (el) {
        if (isCurrency) {
            el.textContent = formatMoney(value, currency).replace(currency || 'USD', '').trim().replace('$', '');
        } else {
            el.textContent = String(value);
        }
    }
}

function updateChangeMetric(valId: string, pctId: string, change: number, pct: number, currency: string): void {
    const valEl = document.getElementById(valId);
    const pctEl = document.getElementById(pctId);

    if (valEl) valEl.textContent = (change >= 0 ? '+' : '') + formatMoney(change, currency);
    if (pctEl) {
        pctEl.textContent = (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';

        // Color classes
        pctEl.className = `text-sm font-medium px-2 py-0.5 rounded ${change >= 0
            ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
            : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'}`;

        if (valEl) {
            valEl.className = `text-2xl font-bold ${change >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`;
        }
    }
}

function renderPerformanceChart(data: PerformanceChartData): void {
    // Clear any existing chart
    const chartEl = document.getElementById('performance-chart');
    if (!chartEl) {
        console.warn('[Dashboard] Performance chart element not found');
        return;
    }

    // Clear previous content
    chartEl.innerHTML = '';

    if (!data || !data.data || !data.layout) {
        chartEl.innerHTML = '<div class="text-center text-gray-500 py-8"><p>No performance data available</p></div>';
        return;
    }

    // Render with Plotly (same as ticker_details.ts)
    const Plotly = (window as any).Plotly;
    if (!Plotly) {
        console.error('[Dashboard] Plotly not loaded');
        chartEl.innerHTML = '<div class="text-center text-red-500 py-8"><p>Error: Plotly library not loaded</p></div>';
        return;
    }

    // Update layout height to match container
    const layout = { ...data.layout };
    layout.height = 320; // Match previous ApexCharts height
    layout.autosize = true;

    try {
        Plotly.newPlot('performance-chart', data.data, layout, { 
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d']
        });
        console.log('[Dashboard] Performance chart rendered with Plotly');
    } catch (error) {
        console.error('[Dashboard] Error rendering Plotly chart:', error);
        chartEl.innerHTML = '<div class="text-center text-red-500 py-8"><p>Error rendering chart</p></div>';
    }
}

function renderSectorChart(data: AllocationChartData): void {
    if (state.charts.sector) {
        state.charts.sector.destroy();
    }

    const chartEl = document.getElementById('sector-chart');
    if (!chartEl) {
        console.warn('[Dashboard] Sector chart element not found');
        return;
    }

    if (!data.sector || data.sector.length === 0) {
        chartEl.innerHTML = '<div class="text-center text-gray-500 py-8"><p>No sector data available</p></div>';
        return;
    }

    const options: ApexChartsOptions = {
        series: data.sector.map(s => s.value),
        chart: {
            type: 'pie',
            height: 320
        },
        labels: data.sector.map(s => s.label),
        tooltip: {
            y: { formatter: (val: number) => formatMoney(val, 'USD') }
        }
    };

    state.charts.sector = new ApexCharts(chartEl, options);
    state.charts.sector.render();
    console.log('[Dashboard] Sector chart rendered');
}

// Expose refreshDashboard globally for template onclick handlers
if (typeof window !== 'undefined') {
    (window as any).refreshDashboard = refreshDashboard;
    console.log('[Dashboard] refreshDashboard function exposed globally');
}
