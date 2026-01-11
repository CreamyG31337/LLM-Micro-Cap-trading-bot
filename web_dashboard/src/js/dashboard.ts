import {
    PortfolioResponse,
    Position,
    Trade,
    ContributorsResponse,
} from './types.js';

// Global state
let portfolioData: PortfolioResponse | null = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupFundSelection();
    initDashboard();

    // Auto-refresh every 5 minutes
    setInterval(initDashboard, 5 * 60 * 1000);
});

// Load portfolio data
async function loadPortfolioData(): Promise<void> {
    try {
        const fundSelect = document.getElementById('fund-select') as HTMLSelectElement | null;
        const fund = fundSelect ? fundSelect.value : '';
        const url = `/api/portfolio?fund=${encodeURIComponent(fund)}`;
        const response = await fetch(url, { credentials: 'include' });

        if (response.status === 401) {
            window.location.href = '/auth';
            return;
        }

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        portfolioData = await response.json();
        if (portfolioData) {
            updateDashboard(portfolioData);
        }
    } catch (error) {
        console.error('Error loading portfolio data:', error);
    }
}

// Load performance chart
async function loadPerformanceChart(): Promise<void> {
    try {
        const fundSelect = document.getElementById('fund-select') as HTMLSelectElement | null;
        const fund = fundSelect ? fundSelect.value : '';
        const url = `/api/performance-chart?fund=${encodeURIComponent(fund)}`;
        const response = await fetch(url, { credentials: 'include' });
        const chartData = await response.json();

        const chartContainer = document.getElementById('performance-chart');
        if (chartContainer) {
            if (chartData && chartData.data) {
                (window as any).Plotly.newPlot('performance-chart', chartData.data, chartData.layout, { responsive: true });
            } else {
                chartContainer.innerHTML =
                    '<div class="text-center text-gray-500 py-8"><p>No performance data available</p></div>';
            }
        }
    } catch (error) {
        console.error('Error loading performance chart:', error);
        const chartContainer = document.getElementById('performance-chart');
        if (chartContainer) {
            chartContainer.innerHTML =
                '<div class="text-center text-red-500 py-8"><p>Error loading chart</p></div>';
        }
    }
}

// Load recent trades
async function loadRecentTrades(): Promise<void> {
    try {
        const fundSelect = document.getElementById('fund-select') as HTMLSelectElement | null;
        const fund = fundSelect ? fundSelect.value : '';
        const url = `/api/recent-trades?fund=${encodeURIComponent(fund)}`;
        const response = await fetch(url, { credentials: 'include' });
        const trades: Trade[] = await response.json();
        displayRecentTrades(trades);
    } catch (error) {
        console.error('Error loading recent trades:', error);
        const container = document.getElementById('trades-container');
        if (container) {
            container.innerHTML =
                '<div class="text-center text-red-500 py-8"><p>Error loading trades</p></div>';
        }
    }
}

// Load contributors
async function loadContributors(): Promise<void> {
    try {
        const fundSelect = document.getElementById('fund-select') as HTMLSelectElement | null;
        const fund = fundSelect ? fundSelect.value : '';
        const container = document.getElementById('contributors-container');

        if (!fund) {
            if (container) {
                container.innerHTML =
                    '<div class="text-center text-gray-500 py-8"><p>Select a fund to view contributors</p></div>';
            }
            return;
        }

        const url = `/api/contributors?fund=${encodeURIComponent(fund)}`;
        const response = await fetch(url, { credentials: 'include' });

        if (response.status === 401) {
            window.location.href = '/auth';
            return;
        }

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: ContributorsResponse = await response.json();
        displayContributors(data);
    } catch (error) {
        console.error('Error loading contributors:', error);
        const container = document.getElementById('contributors-container');
        if (container) {
            container.innerHTML =
                '<div class="text-center text-red-500 py-8"><p>Error loading contributors</p></div>';
        }
    }
}

// Update dashboard with loaded data
function updateDashboard(data: PortfolioResponse): void {
    const metrics = data.metrics || {};
    const positions = data.positions || [];
    const cashBalances = data.cash_balances || {};

    // Update metrics
    const totalValueEl = document.getElementById('total-value');
    if (totalValueEl) {
        totalValueEl.textContent = `$${(metrics.total_value || 0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
    }

    const perfPctEl = document.getElementById('performance-pct');
    if (perfPctEl) {
        perfPctEl.textContent = `${metrics.performance_pct?.toFixed(2) || '0.00'}%`;
        if ((metrics.performance_pct || 0) > 0) {
            perfPctEl.className = 'text-2xl font-bold performance-positive';
        } else if ((metrics.performance_pct || 0) < 0) {
            perfPctEl.className = 'text-2xl font-bold performance-negative';
        } else {
            perfPctEl.className = 'text-2xl font-bold text-gray-900';
        }
    }

    const unrealizedPnlEl = document.getElementById('unrealized-pnl');
    if (unrealizedPnlEl) {
        unrealizedPnlEl.textContent = `$${(metrics.unrealized_pnl || 0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
        if ((metrics.unrealized_pnl || 0) > 0) {
            unrealizedPnlEl.className = 'text-2xl font-bold performance-positive';
        } else if ((metrics.unrealized_pnl || 0) < 0) {
            unrealizedPnlEl.className = 'text-2xl font-bold performance-negative';
        } else {
            unrealizedPnlEl.className = 'text-2xl font-bold text-gray-900';
        }
    }

    const totalTradesEl = document.getElementById('total-trades');
    if (totalTradesEl) {
        totalTradesEl.textContent = (metrics.total_trades || '0').toString();
    }

    // Update cash balances
    const cadBalanceEl = document.getElementById('cad-balance');
    if (cadBalanceEl) {
        cadBalanceEl.textContent = `$${cashBalances.CAD?.toFixed(2) || '0.00'}`;
    }

    const usdBalanceEl = document.getElementById('usd-balance');
    if (usdBalanceEl) {
        usdBalanceEl.textContent = `$${cashBalances.USD?.toFixed(2) || '0.00'}`;
    }

    // Update last updated time
    const lastUpdatedEl = document.getElementById('last-updated');
    if (lastUpdatedEl) {
        lastUpdatedEl.textContent = new Date().toLocaleString();
    }

    // Display positions
    displayPositions(positions);
}

// Display current positions
function displayPositions(positions: Position[]): void {
    const container = document.getElementById('positions-container');
    if (!container) return;

    if (positions.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-500 py-8"><p>No current positions</p></div>';
        return;
    }

    let html = '<div class="space-y-3">';
    positions.forEach(position => {
        const pnlClass = position.pnl >= 0 ? 'text-green-600' : 'text-red-600';
        const pnlPctClass = position.pnl_pct >= 0 ? 'text-green-600' : 'text-red-600';

        html += `
            <div class="border rounded-lg p-4 hover:bg-gray-50">
                <div class="flex justify-between items-start">
                    <div>
                        <h3 class="font-bold text-lg">${position.ticker}</h3>
                        <p class="text-sm text-gray-600">${position.shares} shares @ $${position.price}</p>
                    </div>
                    <div class="text-right">
                        <p class="font-bold">$${position.market_value.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}</p>
                        <p class="text-sm ${pnlClass}">${position.pnl >= 0 ? '+' : ''}$${position.pnl.toFixed(2)}</p>
                        <p class="text-xs ${pnlPctClass}">${position.pnl_pct >= 0 ? '+' : ''}${position.pnl_pct.toFixed(2)}%</p>
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

// Display recent trades
function displayRecentTrades(trades: Trade[]): void {
    const container = document.getElementById('trades-container');
    if (!container) return;

    if (trades.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-500 py-8"><p>No recent trades</p></div>';
        return;
    }

    let html = '<div class="space-y-3">';
    trades.forEach(trade => {
        const pnlClass = trade.pnl >= 0 ? 'text-green-600' : 'text-red-600';
        const actionClass = trade.reason.includes('BUY') ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';

        html += `
            <div class="border rounded-lg p-4 hover:bg-gray-50">
                <div class="flex justify-between items-start">
                    <div>
                        <h3 class="font-bold">${trade.ticker}</h3>
                        <p class="text-sm text-gray-600">${trade.date}</p>
                        <p class="text-xs ${actionClass} px-2 py-1 rounded-full inline-block mt-1">${trade.reason}</p>
                    </div>
                    <div class="text-right">
                        <p class="text-sm">${trade.shares} @ $${trade.price}</p>
                        <p class="font-bold">$${trade.cost_basis.toFixed(2)}</p>
                        ${trade.pnl !== 0 ? `<p class="text-sm ${pnlClass}">${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)}</p>` : ''}
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

function displayContributors(data: ContributorsResponse): void {
    const container = document.getElementById('contributors-container');
    if (!container) return;

    if (!data.contributors || data.contributors.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-500 py-8"><p>No contributors found</p></div>';
        return;
    }

    let html = `
        <div class="mb-4 p-4 bg-blue-50 rounded-lg">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
                <div>
                    <p class="text-sm text-gray-600">Total Contributors</p>
                    <p class="text-2xl font-bold text-blue-600">${data.total_contributors}</p>
                </div>
                <div>
                    <p class="text-sm text-gray-600">Total Contributions</p>
                    <p class="text-2xl font-bold text-green-600">$${data.total_net_contributions.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}</p>
                </div>
                <div>
                    <p class="text-sm text-gray-600">Average per Contributor</p>
                    <p class="text-2xl font-bold text-purple-600">$${(data.total_net_contributions / data.total_contributors).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}</p>
                </div>
            </div>
        </div>
        <div class="space-y-3">
    `;

    data.contributors.forEach((contributor, index) => {
        const rankClass = index === 0 ? 'bg-yellow-50 border-yellow-200' :
            index === 1 ? 'bg-gray-50 border-gray-200' :
                index === 2 ? 'bg-orange-50 border-orange-200' : 'bg-white border-gray-200';

        html += `
            <div class="border rounded-lg p-4 hover:bg-gray-50 ${rankClass}">
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <div class="flex items-center space-x-2">
                            <h3 class="font-bold text-lg">${contributor.contributor}</h3>
                            ${index < 3 ? `<span class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">#${index + 1}</span>` : ''}
                        </div>
                        ${contributor.email ? `<p class="text-sm text-gray-600">${contributor.email}</p>` : ''}
                        <div class="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                            <div>
                                <p class="text-gray-500">Net Contribution</p>
                                <p class="font-bold text-green-600">$${contributor.net_contribution.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}</p>
                            </div>
                            <div>
                                <p class="text-gray-500">Ownership</p>
                                <p class="font-bold text-blue-600">${contributor.ownership_percentage}%</p>
                            </div>
                            <div>
                                <p class="text-gray-500">Transactions</p>
                                <p class="font-bold">${contributor.transaction_count}</p>
                            </div>
                            <div>
                                <p class="text-gray-500">First Contribution</p>
                                <p class="text-xs">${new Date(contributor.first_contribution).toLocaleDateString()}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    container.innerHTML = html;
}

// Load available funds
async function loadFunds(): Promise<void> {
    try {
        const response = await fetch('/api/funds', { credentials: 'include' });
        const data = await response.json();
        const fundSelect = document.getElementById('fund-select') as HTMLSelectElement | null;

        if (fundSelect) {
            // Clear existing options
            fundSelect.innerHTML = '<option value="">Select Fund</option>';

            // Add fund options
            data.funds.forEach((fund: string) => {
                const option = document.createElement('option');
                option.value = fund;
                option.textContent = fund;
                fundSelect.appendChild(option);
            });

            // Set selected fund if provided in URL
            const urlParams = new URLSearchParams(window.location.search);
            const selectedFund = urlParams.get('fund');
            if (selectedFund) {
                fundSelect.value = selectedFund;
            }
        }
    } catch (error) {
        console.error('Error loading funds:', error);
    }
}

// Handle fund selection change
function setupFundSelection(): void {
    const fundSelect = document.getElementById('fund-select') as HTMLSelectElement | null;
    if (fundSelect) {
        fundSelect.addEventListener('change', function (this: HTMLSelectElement) {
            const selectedFund = this.value;

            // Update URL
            const url = new URL(window.location.href);
            if (selectedFund) {
                url.searchParams.set('fund', selectedFund);
            } else {
                url.searchParams.delete('fund');
            }
            window.history.pushState({}, '', url.toString());

            // Reload dashboard data
            reloadDashboardData();
        });
    }
}

// Reload dashboard data without reloading funds list
async function reloadDashboardData(): Promise<void> {
    await Promise.all([
        loadPortfolioData(),
        loadPerformanceChart(),
        loadRecentTrades(),
        loadContributors()
    ]);
}

// Initialize dashboard
async function initDashboard(): Promise<void> {
    // Load funds first (needed for dropdown to work)
    await loadFunds();

    // Then load everything else in parallel
    await reloadDashboardData();
}
