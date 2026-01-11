// Ticker Details Page JavaScript

let currentTicker = '';
let tickerList = [];

// Initialize page on load
document.addEventListener('DOMContentLoaded', function() {
    // Get ticker from URL query parameter
    const urlParams = new URLSearchParams(window.location.search);
    const tickerParam = urlParams.get('ticker');
    
    // Load ticker list first
    loadTickerList().then(() => {
        // If ticker in URL, load it
        if (tickerParam) {
            currentTicker = tickerParam.toUpperCase();
            document.getElementById('ticker-select').value = currentTicker;
            loadTickerData(currentTicker);
        } else {
            // Show placeholder
            showPlaceholder();
        }
    });
    
    // Set up ticker dropdown change handler
    document.getElementById('ticker-select').addEventListener('change', handleTickerSearch);
    
    // Set up chart controls
    document.getElementById('solid-lines-checkbox').addEventListener('change', function() {
        if (currentTicker) {
            loadAndRenderChart(currentTicker, this.checked);
        }
    });
});

// Load ticker list for dropdown
async function loadTickerList() {
    try {
        const response = await fetch('/api/v2/ticker/list', {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Failed to load ticker list');
        }
        
        const data = await response.json();
        tickerList = data.tickers || [];
        
        // Populate dropdown
        const select = document.getElementById('ticker-select');
        // Clear existing options except first one
        while (select.options.length > 1) {
            select.remove(1);
        }
        
        // Add tickers
        tickerList.forEach(ticker => {
            const option = document.createElement('option');
            option.value = ticker;
            option.textContent = ticker;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading ticker list:', error);
    }
}

// Handle ticker search dropdown change
function handleTickerSearch() {
    const selectedTicker = document.getElementById('ticker-select').value.toUpperCase().trim();
    
    if (selectedTicker) {
        // Update URL without reload
        const url = new URL(window.location);
        url.searchParams.set('ticker', selectedTicker);
        window.history.pushState({}, '', url);
        
        currentTicker = selectedTicker;
        loadTickerData(selectedTicker);
    } else {
        // Clear URL and show placeholder
        const url = new URL(window.location);
        url.searchParams.delete('ticker');
        window.history.pushState({}, '', url);
        showPlaceholder();
    }
}

// Load all ticker data
async function loadTickerData(ticker) {
    hideAllSections();
    showLoading();
    hideError();
    hidePlaceholder();
    
    try {
        const response = await fetch(`/api/v2/ticker/info?ticker=${encodeURIComponent(ticker)}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to load ticker data');
        }
        
        const data = await response.json();
        
        // Render all sections
        renderBasicInfo(data.basic_info);
        renderExternalLinks(data.basic_info);
        renderPortfolioData(data.portfolio_data);
        renderResearchArticles(data.research_articles || []);
        renderSocialSentiment(data.social_sentiment);
        renderCongressTrades(data.congress_trades || []);
        renderWatchlistStatus(data.watchlist_status);
        
        // Load and render chart
        const useSolid = document.getElementById('solid-lines-checkbox').checked;
        loadAndRenderChart(ticker, useSolid);
        
        hideLoading();
    } catch (error) {
        console.error('Error loading ticker data:', error);
        showError(error.message);
        hideLoading();
    }
}

// Render basic info section
function renderBasicInfo(basicInfo) {
    if (!basicInfo) {
        return;
    }
    
    const section = document.getElementById('basic-info-section');
    section.classList.remove('section-hidden');
    
    document.getElementById('company-name').textContent = basicInfo.company_name || 'N/A';
    document.getElementById('sector').textContent = basicInfo.sector || 'N/A';
    document.getElementById('industry').textContent = basicInfo.industry || 'N/A';
    document.getElementById('currency').textContent = basicInfo.currency || 'USD';
    
    const exchangeInfo = document.getElementById('exchange-info');
    if (basicInfo.exchange && basicInfo.exchange !== 'N/A') {
        exchangeInfo.textContent = `Exchange: ${basicInfo.exchange}`;
        exchangeInfo.style.display = 'block';
    } else {
        exchangeInfo.style.display = 'none';
    }
}

// Render external links
async function renderExternalLinks(basicInfo) {
    if (!basicInfo || !basicInfo.ticker) {
        return;
    }
    
    try {
        const exchange = basicInfo.exchange || null;
        const response = await fetch(`/api/v2/ticker/external-links?ticker=${encodeURIComponent(basicInfo.ticker)}${exchange ? `&exchange=${encodeURIComponent(exchange)}` : ''}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            return;
        }
        
        const links = await response.json();
        const grid = document.getElementById('external-links-grid');
        grid.innerHTML = '';
        
        Object.entries(links).forEach(([name, url]) => {
            const link = document.createElement('a');
            link.href = url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.className = 'external-link';
            link.textContent = name;
            grid.appendChild(link);
        });
        
        if (Object.keys(links).length > 0) {
            document.getElementById('external-links-section').classList.remove('section-hidden');
        }
    } catch (error) {
        console.error('Error loading external links:', error);
    }
}

// Render portfolio data
function renderPortfolioData(portfolioData) {
    if (!portfolioData || (!portfolioData.has_positions && !portfolioData.has_trades)) {
        return;
    }
    
    const section = document.getElementById('portfolio-section');
    section.classList.remove('section-hidden');
    
    // Render positions
    if (portfolioData.has_positions && portfolioData.positions && portfolioData.positions.length > 0) {
        const tbody = document.getElementById('positions-tbody');
        tbody.innerHTML = '';
        
        // Get latest position per fund
        const latestPositions = {};
        portfolioData.positions.forEach(pos => {
            const fund = pos.fund || 'Unknown';
            if (!latestPositions[fund] || (pos.date && pos.date > (latestPositions[fund].date || ''))) {
                latestPositions[fund] = pos;
            }
        });
        
        Object.values(latestPositions).forEach(pos => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${pos.fund || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${formatNumber(pos.shares || 0, 2)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${formatCurrency(pos.price || 0)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${formatCurrency(pos.cost_basis || 0)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm ${(pos.pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}">${formatCurrency(pos.pnl || 0)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${formatDate(pos.date)}</td>
            `;
            tbody.appendChild(row);
        });
        
        document.getElementById('positions-container').style.display = 'block';
    } else {
        document.getElementById('positions-container').style.display = 'none';
    }
    
    // Render trades
    if (portfolioData.has_trades && portfolioData.trades && portfolioData.trades.length > 0) {
        const tbody = document.getElementById('trades-tbody');
        tbody.innerHTML = '';
        
        portfolioData.trades.slice(0, 20).forEach(trade => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${formatDate(trade.date)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${trade.action || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${formatNumber(trade.shares || 0, 2)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${formatCurrency(trade.price || 0)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${trade.fund || 'N/A'}</td>
                <td class="px-6 py-4 text-sm text-gray-500">${(trade.reason || 'N/A').substring(0, 50)}</td>
            `;
            tbody.appendChild(row);
        });
    }
}

// Load and render chart
async function loadAndRenderChart(ticker, useSolid) {
    // Show loading indicator
    const chartLoading = document.getElementById('chart-loading');
    const chartContainer = document.getElementById('chart-container');
    
    // Clear any existing chart
    chartContainer.innerHTML = '';
    chartLoading.classList.remove('section-hidden');
    
    // Show chart section (but with loading indicator)
    document.getElementById('chart-section').classList.remove('section-hidden');
    
    try {
        // Detect actual theme from page
        const htmlElement = document.documentElement;
        const dataTheme = htmlElement.getAttribute('data-theme') || 'system';
        let theme = 'light'; // default
        
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
        
        console.log('Detected theme:', theme, 'from data-theme:', dataTheme);
        
        const response = await fetch(`/api/v2/ticker/chart?ticker=${encodeURIComponent(ticker)}&use_solid=${useSolid}&theme=${encodeURIComponent(theme)}`, {
            credentials: 'include'
        });
        
        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        const isJson = contentType && contentType.includes('application/json');
        
        if (!response.ok) {
            let errorMessage = `Failed to load chart (${response.status})`;
            if (isJson) {
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorMessage;
                } catch (e) {
                    // If JSON parsing fails, use default message
                }
            } else {
                // Response is HTML (likely an error page)
                errorMessage = `Server error: ${response.status} ${response.statusText}`;
            }
            throw new Error(errorMessage);
        }
        
        if (!isJson) {
            throw new Error('Server returned non-JSON response. Please check your authentication.');
        }
        
        const chartData = await response.json();
        
        // Validate chart data structure
        if (!chartData || !chartData.data || !chartData.layout) {
            throw new Error('Invalid chart data received from server');
        }
        
        // Render with Plotly
        Plotly.newPlot('chart-container', chartData.data, chartData.layout, {responsive: true});
        
        // Hide loading indicator AFTER successful rendering
        chartLoading.classList.add('section-hidden');
        chartLoading.style.display = 'none';
        
        // Load price history for metrics
        loadPriceHistoryMetrics(ticker);
    } catch (error) {
        console.error('Error loading chart:', error);
        // Hide loading indicator
        chartLoading.classList.add('section-hidden');
        // Show error message to user
        showError(`Failed to load chart: ${error.message}`);
        // Hide chart section on error
        document.getElementById('chart-section').classList.add('section-hidden');
    }
}

// Load price history for metrics
async function loadPriceHistoryMetrics(ticker) {
    try {
        const response = await fetch(`/api/v2/ticker/price-history?ticker=${encodeURIComponent(ticker)}&days=90`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            return;
        }
        
        const data = await response.json();
        const prices = data.data || [];
        
        if (prices.length > 0) {
            const firstPrice = prices[0].price || 0;
            const lastPrice = prices[prices.length - 1].price || 0;
            const priceChange = lastPrice - firstPrice;
            const priceChangePct = firstPrice > 0 ? (priceChange / firstPrice * 100) : 0;
            
            document.getElementById('first-price').textContent = formatCurrency(firstPrice);
            document.getElementById('last-price').textContent = formatCurrency(lastPrice);
            const changeEl = document.getElementById('price-change');
            changeEl.textContent = `${priceChangePct >= 0 ? '+' : ''}${priceChangePct.toFixed(2)}%`;
            changeEl.className = `text-xl font-semibold ${priceChangePct >= 0 ? 'text-green-600' : 'text-red-600'}`;
        }
    } catch (error) {
        console.error('Error loading price history metrics:', error);
    }
}

// Render research articles
function renderResearchArticles(articles) {
    if (!articles || articles.length === 0) {
        return;
    }
    
    const section = document.getElementById('research-section');
    section.classList.remove('section-hidden');
    
    document.getElementById('research-count').textContent = `Found ${articles.length} articles mentioning ${currentTicker} (last 30 days)`;
    
    const list = document.getElementById('research-articles-list');
    list.innerHTML = '';
    
    articles.slice(0, 10).forEach(article => {
        const articleDiv = document.createElement('div');
        articleDiv.className = 'border-b border-gray-200 py-4';
        
        const title = article.title || 'Untitled';
        const summary = article.summary || '';
        const url = article.url || '#';
        const source = article.source || 'Unknown';
        const publishedAt = formatDate(article.published_at);
        const sentiment = article.sentiment || 'N/A';
        
        const summaryId = `summary-${article.id || Math.random().toString(36).substr(2, 9)}`;
        const isLongSummary = summary.length > 500;
        const shortSummary = isLongSummary ? summary.substring(0, 500) + '...' : summary;
        
        articleDiv.innerHTML = `
            <details class="cursor-pointer">
                <summary class="font-semibold text-blue-600 hover:text-blue-800">${title}</summary>
                <div class="mt-2 pl-4">
                    <div id="${summaryId}-short" class="text-gray-700 mb-2">${shortSummary}</div>
                    ${isLongSummary ? `
                        <div id="${summaryId}-full" class="hidden text-gray-700 mb-2 whitespace-pre-wrap">${summary}</div>
                        <button onclick="toggleSummary('${summaryId}')" class="text-blue-600 hover:text-blue-800 text-sm font-medium mb-2">
                            <span id="${summaryId}-toggle">Show Full Summary</span>
                        </button>
                    ` : ''}
                    <div class="flex justify-between items-center text-sm text-gray-500">
                        <div>
                            <span>Source: ${source}</span>
                            ${publishedAt ? `<span class="ml-4">Published: ${publishedAt}</span>` : ''}
                            ${sentiment !== 'N/A' ? `<span class="ml-4">Sentiment: ${sentiment}</span>` : ''}
                        </div>
                        <a href="${url}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:text-blue-800">Read Full Article →</a>
                    </div>
                </div>
            </details>
        `;
        list.appendChild(articleDiv);
    });
}

// Render social sentiment
function renderSocialSentiment(sentiment) {
    if (!sentiment) {
        return;
    }
    
    const section = document.getElementById('sentiment-section');
    section.classList.remove('section-hidden');
    
    // Render metrics
    if (sentiment.latest_metrics && sentiment.latest_metrics.length > 0) {
        const tbody = document.getElementById('sentiment-tbody');
        tbody.innerHTML = '';
        
        sentiment.latest_metrics.forEach(metric => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${(metric.platform || 'N/A').charAt(0).toUpperCase() + (metric.platform || '').slice(1)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${metric.sentiment_label || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${(metric.sentiment_score || 0).toFixed(2)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${metric.volume || 0}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${metric.bull_bear_ratio !== null && metric.bull_bear_ratio !== undefined ? metric.bull_bear_ratio.toFixed(2) : 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${formatDate(metric.created_at)}</td>
            `;
            tbody.appendChild(row);
        });
        
        document.getElementById('sentiment-metrics-container').style.display = 'block';
    } else {
        document.getElementById('sentiment-metrics-container').style.display = 'none';
    }
    
    // Render alerts
    if (sentiment.alerts && sentiment.alerts.length > 0) {
        const alertsList = document.getElementById('sentiment-alerts-list');
        alertsList.innerHTML = '';
        
        sentiment.alerts.forEach(alert => {
            const alertDiv = document.createElement('div');
            const platform = (alert.platform || 'Unknown').charAt(0).toUpperCase() + (alert.platform || '').slice(1);
            const sentimentLabel = alert.sentiment_label || 'N/A';
            const score = (alert.sentiment_score || 0).toFixed(2);
            
            let alertClass = 'bg-blue-100 border-blue-400 text-blue-700';
            if (sentimentLabel === 'EUPHORIC') {
                alertClass = 'bg-green-100 border-green-400 text-green-700';
            } else if (sentimentLabel === 'FEARFUL') {
                alertClass = 'bg-red-100 border-red-400 text-red-700';
            } else if (sentimentLabel === 'BULLISH') {
                alertClass = 'bg-blue-100 border-blue-400 text-blue-700';
            }
            
            alertDiv.className = `border px-4 py-3 rounded mb-2 ${alertClass}`;
            alertDiv.textContent = `${platform} - ${sentimentLabel} (Score: ${score})`;
            alertsList.appendChild(alertDiv);
        });
        
        document.getElementById('sentiment-alerts-container').style.display = 'block';
    } else {
        document.getElementById('sentiment-alerts-container').style.display = 'none';
    }
}

// Render congress trades
function renderCongressTrades(trades) {
    if (!trades || trades.length === 0) {
        return;
    }
    
    const section = document.getElementById('congress-section');
    section.classList.remove('section-hidden');
    
    document.getElementById('congress-count').textContent = `Found ${trades.length} recent trades by politicians (last 30 days)`;
    
    const tbody = document.getElementById('congress-tbody');
    tbody.innerHTML = '';
    
    trades.slice(0, 20).forEach(trade => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${formatDate(trade.transaction_date)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${trade.politician || 'N/A'}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${trade.chamber || 'N/A'}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${trade.type || 'N/A'}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${trade.amount || 'N/A'}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${trade.party || 'N/A'}</td>
        `;
        tbody.appendChild(row);
    });
}

// Render watchlist status
function renderWatchlistStatus(status) {
    if (!status) {
        return;
    }
    
    const section = document.getElementById('watchlist-section');
    section.classList.remove('section-hidden');
    
    document.getElementById('watchlist-status').textContent = status.is_active ? '✅ In Watchlist' : '❌ Not Active';
    document.getElementById('watchlist-tier').textContent = status.priority_tier || 'N/A';
    document.getElementById('watchlist-source').textContent = status.source || 'N/A';
}

// Utility functions
function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString();
    } catch (e) {
        return dateStr.substring(0, 10); // Return first 10 chars if parsing fails
    }
}

function formatCurrency(value) {
    return `$${parseFloat(value || 0).toFixed(2)}`;
}

function formatNumber(value, decimals = 2) {
    return parseFloat(value || 0).toFixed(decimals);
}

function showLoading() {
    document.getElementById('loading-spinner').classList.remove('section-hidden');
}

function hideLoading() {
    document.getElementById('loading-spinner').classList.add('section-hidden');
}

function showError(message) {
    document.getElementById('error-text').textContent = message;
    document.getElementById('error-message').classList.remove('section-hidden');
}

function hideError() {
    document.getElementById('error-message').classList.add('section-hidden');
}

function toggleSummary(summaryId) {
    const shortDiv = document.getElementById(`${summaryId}-short`);
    const fullDiv = document.getElementById(`${summaryId}-full`);
    const toggleBtn = document.getElementById(`${summaryId}-toggle`);
    
    if (shortDiv && fullDiv && toggleBtn) {
        if (fullDiv.classList.contains('hidden')) {
            // Show full summary
            shortDiv.classList.add('hidden');
            fullDiv.classList.remove('hidden');
            toggleBtn.textContent = 'Show Less';
        } else {
            // Show short summary
            shortDiv.classList.remove('hidden');
            fullDiv.classList.add('hidden');
            toggleBtn.textContent = 'Show Full Summary';
        }
    }
}

function showPlaceholder() {
    document.getElementById('placeholder-message').classList.remove('section-hidden');
    hideAllSections();
}

function hidePlaceholder() {
    document.getElementById('placeholder-message').classList.add('section-hidden');
}

function hideAllSections() {
    const sections = [
        'basic-info-section',
        'external-links-section',
        'portfolio-section',
        'chart-section',
        'research-section',
        'sentiment-section',
        'congress-section',
        'watchlist-section'
    ];
    
    sections.forEach(id => {
        document.getElementById(id).classList.add('section-hidden');
    });
}
