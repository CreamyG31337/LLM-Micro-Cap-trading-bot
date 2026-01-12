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
    series: Array<{
        name: string;
        data: Array<[number, number]>; // [timestamp_ms, value]
    }>;
    color: string;
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
    currentFund: typeof INITIAL_FUND !== 'undefined' && INITIAL_FUND ? INITIAL_FUND : '',
    timeRange: 'ALL' as '1M' | '3M' | '6M' | '1Y' | 'ALL',
    charts: {} as Record<string, ApexCharts>,
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
    const selector = document.getElementById('dashboard-fund-select') as HTMLSelectElement | null;
    console.log('[Dashboard] Initializing fund selector...');
    
    if (!selector) {
        console.error('[Dashboard] Fund selector element not found!');
        return;
    }
    
    try {
        const response = await fetch('/api/funds', { credentials: 'include' });
        console.log('[Dashboard] Funds API response:', {
            status: response.status,
            ok: response.ok
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data: Fund[] | { funds: Fund[] } = await response.json();
        console.log('[Dashboard] Funds data received:', {
            fund_count: Array.isArray(data) ? data.length : (data.funds ? data.funds.length : 0),
            funds: Array.isArray(data) ? data.map(f => f.name) : (data.funds || []).map((f: Fund) => f.name)
        });
        
        // Clear except "All" (or keep All if desired)
        selector.innerHTML = '';

        // Keep "All Funds" option if it was default
        const allOpt = document.createElement('option');
        allOpt.value = ''; // Empty string = None for backend
        allOpt.textContent = 'All Funds';
        selector.appendChild(allOpt);

        // Handle both array and object response formats
        const funds = Array.isArray(data) ? data : (data.funds || []);
        funds.forEach(fund => {
            const opt = document.createElement('option');
            opt.value = fund.name;
            opt.textContent = fund.name;
            selector.appendChild(opt);
        });

        // Set initial selected
        if (state.currentFund && state.currentFund !== 'All') {
            selector.value = state.currentFund;
        } else {
            selector.value = '';
        }

        // Listen for changes
        selector.addEventListener('change', (e: Event): void => {
            const target = e.target as HTMLSelectElement;
            state.currentFund = target.value;
            console.log('[Dashboard] Fund changed to:', state.currentFund);
            refreshDashboard();
        });

    } catch (error) {
        console.error('[Dashboard] Error loading funds:', {
            error: error,
            message: error instanceof Error ? error.message : String(error),
            stack: error instanceof Error ? error.stack : undefined
        });
    }
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

    state.gridApi = (window as any).agGrid.createGrid(gridEl, gridOptions);
    console.log('[Dashboard] AG Grid initialized');
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
    const url = `/api/dashboard/charts/performance?fund=${encodeURIComponent(state.currentFund)}&range=${state.timeRange}`;
    const startTime = performance.now();
    
    console.log('[Dashboard] Fetching performance chart...', { url, fund: state.currentFund, range: state.timeRange });
    
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
            console.error('[Dashboard] Performance chart API error:', {
                status: response.status,
                errorData: errorData,
                url: url
            });
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data: PerformanceChartData = await response.json();
        console.log('[Dashboard] Performance chart data received', {
            series_count: data.series ? data.series.length : 0,
            data_points: data.series && data.series[0] ? data.series[0].data.length : 0,
            color: data.color
        });

        renderPerformanceChart(data);

    } catch (error) {
        const duration = performance.now() - startTime;
        console.error('[Dashboard] Error fetching performance chart:', {
            error: error,
            message: error instanceof Error ? error.message : String(error),
            url: url,
            duration: `${duration.toFixed(2)}ms`
        });
        const chartEl = document.getElementById('performance-chart');
        if (chartEl) {
            chartEl.innerHTML = `<div class="text-center text-red-500 py-8"><p>Error loading chart: ${error instanceof Error ? error.message : 'Unknown error'}</p></div>`;
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
            console.error('[Dashboard] Holdings API error:', {
                status: response.status,
                errorData: errorData,
                url: url
            });
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data: HoldingsData = await response.json();
        const rowCount = data.data ? data.data.length : 0;
        console.log('[Dashboard] Holdings data received', {
            row_count: rowCount,
            has_grid_api: !!state.gridApi
        });

        if (state.gridApi) {
            state.gridApi.setRowData(data.data || []);
            console.log('[Dashboard] Holdings grid updated with', rowCount, 'rows');
        } else {
            console.warn('[Dashboard] Grid API not initialized, cannot update holdings');
        }

    } catch (error) {
        const duration = performance.now() - startTime;
        console.error('[Dashboard] Error fetching holdings:', {
            error: error,
            message: error instanceof Error ? error.message : String(error),
            url: url,
            duration: `${duration.toFixed(2)}ms`
        });
        const gridEl = document.getElementById('holdings-grid');
        if (gridEl) {
            gridEl.innerHTML = `<div class="text-center text-red-500 py-8"><p>Error loading holdings: ${error instanceof Error ? error.message : 'Unknown error'}</p></div>`;
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

        valEl.className = `text-2xl font-bold ${change >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`;
    }
}

function renderPerformanceChart(data: PerformanceChartData): void {
    if (state.charts.performance) {
        state.charts.performance.destroy();
    }

    const chartEl = document.getElementById('performance-chart');
    if (!chartEl) {
        console.warn('[Dashboard] Performance chart element not found');
        return;
    }

    if (!data.series || !data.series[0] || !data.series[0].data || data.series[0].data.length === 0) {
        chartEl.innerHTML = '<div class="text-center text-gray-500 py-8"><p>No performance data available</p></div>';
        return;
    }

    const options: ApexCharts.ApexOptions = {
        series: data.series,
        chart: {
            type: 'line',
            height: 320,
            toolbar: { show: false },
            zoom: { enabled: true }
        },
        colors: [data.color || '#10B981'],
        stroke: { curve: 'smooth', width: 2 },
        xaxis: {
            type: 'datetime'
        },
        yaxis: {
            labels: {
                formatter: (val: number) => formatMoney(val, 'USD')
            }
        },
        tooltip: {
            x: { format: 'MMM dd, yyyy' },
            y: { formatter: (val: number) => formatMoney(val, 'USD') }
        }
    };

    state.charts.performance = new ApexCharts(chartEl, options);
    state.charts.performance.render();
    console.log('[Dashboard] Performance chart rendered');
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

    const options: ApexCharts.ApexOptions = {
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
