/**
 * AI Assistant JavaScript
 * Handles chat interface, streaming responses, context management, and search
 */

class AIAssistant {
    constructor(config) {
        this.config = config;
        this.messages = [];
        this.contextItems = [];
        this.selectedModel = config.defaultModel || 'granite3.2:8b';
        this.selectedFund = config.availableFunds?.[0] || null;
        this.conversationHistory = [];
        this.includeSearch = true;
        this.includeRepository = true;
        this.includePriceVolume = true;
        this.includeFundamentals = true;
        this.contextCache = null;
        this.contextFingerprint = null;
    }

    init() {
        this.setupEventListeners();
        this.loadModels();
        this.loadFunds();
        this.loadContextItems();
        this.updateUI();
    }

    setupEventListeners() {
        // Send button
        const sendBtn = document.getElementById('send-btn');
        const chatInput = document.getElementById('chat-input');
        
        sendBtn.addEventListener('click', () => this.sendMessage());
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Clear chat
        document.getElementById('clear-chat-btn').addEventListener('click', () => this.clearChat());

        // Model selection
        document.getElementById('model-select').addEventListener('change', (e) => {
            this.selectedModel = e.target.value;
            this.saveModelPreference();
        });

        // Fund selection
        document.getElementById('fund-select').addEventListener('change', (e) => {
            this.selectedFund = e.target.value;
            this.clearChat(); // Clear chat when fund changes
            this.loadPortfolioTickers(); // Reload tickers for new fund
        });

        // Context toggles
        document.getElementById('toggle-thesis').addEventListener('change', (e) => {
            this.updateContextItem('thesis', e.target.checked);
        });
        document.getElementById('toggle-trades').addEventListener('change', (e) => {
            this.updateContextItem('trades', e.target.checked);
        });
        document.getElementById('toggle-price-volume').addEventListener('change', (e) => {
            this.includePriceVolume = e.target.checked;
        });
        document.getElementById('toggle-fundamentals').addEventListener('change', (e) => {
            this.includeFundamentals = e.target.checked;
        });
        document.getElementById('toggle-search').addEventListener('change', (e) => {
            this.includeSearch = e.target.checked;
        });
        document.getElementById('toggle-repository').addEventListener('change', (e) => {
            this.includeRepository = e.target.checked;
        });

        // Clear context
        document.getElementById('clear-context-btn').addEventListener('click', () => this.clearContext());

        // Retry last response button
        document.getElementById('retry-btn').addEventListener('click', () => this.retryLastMessage());

        // Portfolio Intelligence button
        document.getElementById('portfolio-intelligence-btn').addEventListener('click', () => this.checkPortfolioNews());

        // Quick research buttons
        document.getElementById('research-ticker-btn').addEventListener('click', () => this.quickResearch('research'));
        document.getElementById('analyze-ticker-btn').addEventListener('click', () => this.quickResearch('analyze'));
        document.getElementById('compare-tickers-btn').addEventListener('click', () => this.quickResearch('compare'));
        document.getElementById('earnings-ticker-btn').addEventListener('click', () => this.quickResearch('earnings'));
        document.getElementById('portfolio-analysis-btn').addEventListener('click', () => this.quickResearch('portfolio'));
        document.getElementById('market-news-btn').addEventListener('click', () => this.quickResearch('market'));
        document.getElementById('sector-news-btn').addEventListener('click', () => this.quickResearch('sector'));

        // Ticker selection
        document.getElementById('ticker-select').addEventListener('change', () => this.updateTickerActions());
        document.getElementById('custom-ticker').addEventListener('input', () => this.updateTickerActions());

        // Suggested prompt handlers
        document.getElementById('send-edited-prompt-btn').addEventListener('click', () => {
            const prompt = document.getElementById('editable-prompt').value;
            document.getElementById('suggested-prompt-area').classList.add('hidden');
            this.sendMessage(prompt);
        });
        document.getElementById('cancel-edited-prompt-btn').addEventListener('click', () => {
            document.getElementById('suggested-prompt-area').classList.add('hidden');
        });
        document.getElementById('run-analysis-btn').addEventListener('click', () => {
            const prompt = document.getElementById('initial-prompt').value;
            document.getElementById('start-analysis-area').classList.add('hidden');
            this.sendMessage(prompt);
        });
    }

    loadModels() {
        fetch('/api/v2/ai/models')
            .then(res => res.json())
            .then(data => {
                const select = document.getElementById('model-select');
                select.innerHTML = '';
                data.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model.id;
                    option.textContent = model.name;
                    if (model.id === this.selectedModel) {
                        option.selected = true;
                    }
                    select.appendChild(option);
                });
                this.updateModelDescription();
            })
            .catch(err => console.error('Error loading models:', err));
    }

    loadFunds() {
        const select = document.getElementById('fund-select');
        this.config.availableFunds.forEach(fund => {
            const option = document.createElement('option');
            option.value = fund;
            option.textContent = fund;
            if (fund === this.selectedFund) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    }

    loadContextItems() {
        fetch('/api/v2/ai/context')
            .then(res => res.json())
            .then(data => {
                this.contextItems = data.items || [];
                this.updateContextUI();
            })
            .catch(err => console.error('Error loading context:', err));
    }

    updateContextItem(itemType, enabled) {
        const action = enabled ? 'add' : 'remove';
        const metadata = itemType === 'trades' ? { limit: 50 } : {};
        
        fetch('/api/v2/ai/context', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: action,
                item_type: itemType,
                fund: this.selectedFund,
                metadata: metadata
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                this.loadContextItems();
            }
        })
        .catch(err => console.error('Error updating context:', err));
    }

    clearContext() {
        fetch('/api/v2/ai/context', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'clear' })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                this.contextItems = [];
                this.updateContextUI();
                // Uncheck all toggles
                document.getElementById('toggle-thesis').checked = false;
                document.getElementById('toggle-trades').checked = false;
            }
        })
        .catch(err => console.error('Error clearing context:', err));
    }

    updateContextUI() {
        const summary = document.getElementById('context-summary');
        if (this.contextItems.length === 0) {
            summary.textContent = 'No context items selected';
        } else {
            summary.textContent = `✅ ${this.contextItems.length} data source(s) selected`;
        }
        document.getElementById('context-items').textContent = `Context Items: ${this.contextItems.length}`;
        
        // Invalidate context cache when items change
        this.contextFingerprint = null;
        this.contextCache = null;
    }

    updateModelDescription() {
        const model = this.selectedModel;
        const desc = document.getElementById('model-description');
        
        if (model.startsWith('gemini-')) {
            desc.textContent = 'Web-based AI model with persistent conversations';
        } else {
            desc.textContent = 'Local Ollama model';
        }
    }

    updateTickerActions() {
        const select = document.getElementById('ticker-select');
        const custom = document.getElementById('custom-ticker').value.trim().toUpperCase();
        const selected = Array.from(select.selectedOptions).map(opt => opt.value);
        const activeTickers = custom ? [...selected, custom] : selected;
        
        const actionsDiv = document.getElementById('ticker-actions');
        if (activeTickers.length > 0) {
            actionsDiv.classList.remove('hidden');
            document.getElementById('compare-tickers-btn').classList.toggle('hidden', activeTickers.length < 2);
        } else {
            actionsDiv.classList.add('hidden');
        }
    }

    async sendMessage(userQuery = null) {
        const query = userQuery || document.getElementById('chat-input').value.trim();
        if (!query) return;

        // Clear input
        document.getElementById('chat-input').value = '';

        // Add user message
        this.addMessage('user', query);
        this.conversationHistory.push({ role: 'user', content: query });

        // Hide start analysis area and retry button
        document.getElementById('start-analysis-area').classList.add('hidden');
        document.getElementById('retry-button-container').classList.add('hidden');

        // Show loading indicator
        const loadingId = this.addMessage('assistant', '🧠 Generating response...', true);

        // Perform search if enabled
        let searchResults = null;
        let repositoryArticles = null;

        if (this.includeSearch && this.config.searxngAvailable) {
            try {
                searchResults = await this.performSearch(query);
            } catch (err) {
                console.error('Search error:', err);
            }
        }

        if (this.includeRepository && this.config.ollamaAvailable) {
            try {
                repositoryArticles = await this.performRepositorySearch(query);
            } catch (err) {
                console.error('Repository search error:', err);
            }
        }

        // Get cached context
        const contextString = await this.getCachedContext();

        // Build request
        const requestData = {
            query: query,
            model: this.selectedModel,
            fund: this.selectedFund,
            context_items: this.contextItems,
            context_string: contextString, // Pre-built context string
            conversation_history: this.conversationHistory.slice(-20), // Last 20 messages
            include_search: this.includeSearch,
            include_repository: this.includeRepository,
            include_price_volume: this.includePriceVolume,
            include_fundamentals: this.includeFundamentals,
            search_results: searchResults,
            repository_articles: repositoryArticles
        };

        // Check if streaming (Ollama) or non-streaming (WebAI)
        if (this.selectedModel.startsWith('gemini-')) {
            // WebAI - non-streaming
            this.sendWebAIMessage(requestData, loadingId);
        } else {
            // Ollama - streaming
            this.sendStreamingMessage(requestData, loadingId);
        }
    }

    getContextFingerprint() {
        // Create fingerprint from context items
        const items = this.contextItems.map(item => 
            `${item.item_type}:${item.fund || ''}:${JSON.stringify(item.metadata || {})}`
        ).sort().join('|');
        return items;
    }

    async getCachedContext() {
        // Check if context has changed
        const fingerprint = this.getContextFingerprint();
        if (fingerprint === this.contextFingerprint && this.contextCache) {
            return this.contextCache;
        }

        // Build context from API
        try {
            const response = await fetch('/api/v2/ai/context/build', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    fund: this.selectedFund,
                    include_price_volume: this.includePriceVolume,
                    include_fundamentals: this.includeFundamentals
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.contextCache = data.context_string || '';
                this.contextFingerprint = fingerprint;
                return this.contextCache;
            }
        } catch (err) {
            this.showError('Error building context: ' + err.message);
        }

        return '';
    }

    async performSearch(query) {
        // Extract tickers from query (simple implementation)
        const tickers = this.extractTickers(query);
        
        const response = await fetch('/api/v2/ai/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                tickers: tickers,
                time_range: 'day',
                min_relevance_score: 0.3
            })
        });

        if (!response.ok) {
            throw new Error('Search failed');
        }

        const data = await response.json();
        return data;
    }

    async performRepositorySearch(query) {
        const response = await fetch('/api/v2/ai/repository', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                max_results: 3,
                min_similarity: 0.6
            })
        });

        if (!response.ok) {
            throw new Error('Repository search failed');
        }

        const data = await response.json();
        return data.articles || [];
    }

    extractTickers(query) {
        // Simple ticker extraction (uppercase words that look like tickers)
        const words = query.toUpperCase().split(/\s+/);
        const tickers = words.filter(word => 
            word.length <= 5 && 
            /^[A-Z]+$/.test(word) && 
            word.length >= 1
        );
        return tickers;
    }

    sendWebAIMessage(requestData, loadingId) {
        fetch('/api/v2/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                this.updateMessage(loadingId, 'assistant', `Error: ${data.error}`);
            } else {
                this.updateMessage(loadingId, 'assistant', data.response);
                this.conversationHistory.push({ role: 'assistant', content: data.response });
            }
        })
        .catch(err => {
            console.error('Chat error:', err);
            this.updateMessage(loadingId, 'assistant', `Error: ${err.message}`);
        });
    }

    sendStreamingMessage(requestData, loadingId) {
        fetch('/api/v2/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        })
        .then(res => {
            if (!res.ok) {
                return res.json().then(data => {
                    throw new Error(data.error || `HTTP error! status: ${res.status}`);
                });
            }

            // Check if response is SSE (text/event-stream) or JSON
            const contentType = res.headers.get('content-type');
            if (contentType && contentType.includes('text/event-stream')) {
                // SSE streaming
                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let fullResponse = '';

                const readChunk = () => {
                    reader.read().then(({ done, value }) => {
                        if (done) {
                            // Remove streaming indicator and finalize
                            this.updateMessage(loadingId, 'assistant', fullResponse);
                            this.conversationHistory.push({ role: 'assistant', content: fullResponse });
                            this.updateRetryButton();
                            return;
                        }

                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        buffer = lines.pop() || ''; // Keep incomplete line in buffer

                        for (const line of lines) {
                            if (line.trim() === '') continue;
                            if (line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.slice(6));
                                    if (data.done) {
                                        this.updateMessage(loadingId, 'assistant', fullResponse);
                                        this.conversationHistory.push({ role: 'assistant', content: fullResponse });
                                        this.updateRetryButton();
                                        return;
                                    }
                                    if (data.chunk) {
                                        fullResponse += data.chunk;
                                        this.updateMessage(loadingId, 'assistant', fullResponse + '<span class="streaming-indicator">▌</span>');
                                    }
                                    if (data.error) {
                                        this.updateMessage(loadingId, 'assistant', `❌ Error: ${data.error}`);
                                        this.updateRetryButton();
                                        return;
                                    }
                                } catch (e) {
                                    console.error('Error parsing SSE data:', e, 'Line:', line);
                                }
                            }
                        }

                        readChunk();
                    }).catch(err => {
                        this.updateMessage(loadingId, 'assistant', `❌ Error: ${err.message}`);
                        this.updateRetryButton();
                    });
                };

                readChunk();
            } else {
                // Non-streaming JSON response (fallback)
                return res.json().then(data => {
                    if (data.error) {
                        this.updateMessage(loadingId, 'assistant', `❌ Error: ${data.error}`);
                        this.updateRetryButton();
                    } else {
                        this.updateMessage(loadingId, 'assistant', data.response || data.chunk || '');
                        this.conversationHistory.push({ role: 'assistant', content: data.response || data.chunk || '' });
                        this.updateRetryButton();
                    }
                });
            }
        })
        .catch(err => {
            console.error('Chat error:', err);
            this.updateMessage(loadingId, 'assistant', `Error: ${err.message}`);
        });
    }

    addMessage(role, content, isLoading = false) {
        const messagesDiv = document.getElementById('chat-messages');
        const messageId = `msg-${Date.now()}-${Math.random()}`;
        
        const messageDiv = document.createElement('div');
        messageDiv.id = messageId;
        messageDiv.className = `chat-message ${role}`;
        
        const bubble = document.createElement('div');
        bubble.className = `message-bubble ${role}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        if (isLoading) {
            contentDiv.innerHTML = content;
        } else {
            contentDiv.innerHTML = this.renderMarkdown(content);
        }
        
        bubble.appendChild(contentDiv);
        messageDiv.appendChild(bubble);
        messagesDiv.appendChild(messageDiv);
        
        this.scrollToBottom();
        
        return messageId;
    }

    updateMessage(messageId, role, content) {
        const messageDiv = document.getElementById(messageId);
        if (!messageDiv) return;
        
        const contentDiv = messageDiv.querySelector('.message-content');
        if (contentDiv) {
            // Check if this is an error message
            if (content.includes('Error:') || content.includes('error:')) {
                messageDiv.classList.add('error-message');
            }
            contentDiv.innerHTML = this.renderMarkdown(content);
        }
        
        this.scrollToBottom();
    }

    renderMarkdown(text) {
        if (typeof marked !== 'undefined') {
            const html = marked.parse(text);
            // Sanitize HTML to prevent XSS attacks
            if (typeof DOMPurify !== 'undefined') {
                return DOMPurify.sanitize(html, {
                    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'a'],
                    ALLOWED_ATTR: ['href', 'title']
                });
            }
            return html;
        }
        // Fallback: simple text rendering (escape HTML)
        return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
    }

    scrollToBottom() {
        const container = document.getElementById('chat-container');
        container.scrollTop = container.scrollHeight;
    }

    clearChat() {
        this.messages = [];
        this.conversationHistory = [];
        document.getElementById('chat-messages').innerHTML = '';
        document.getElementById('retry-button-container').classList.add('hidden');
        
        // Show start analysis area if context items exist
        if (this.contextItems.length > 0) {
            this.showStartAnalysis();
        }
    }

    showStartAnalysis() {
        const area = document.getElementById('start-analysis-area');
        area.classList.remove('hidden');
        // Generate default prompt
        const prompt = this.generateDefaultPrompt();
        document.getElementById('initial-prompt').value = prompt;
    }

    generateDefaultPrompt() {
        if (this.contextItems.length === 0) {
            return "Please help me analyze my portfolio.";
        }
        
        const itemTypes = this.contextItems.map(item => item.item_type);
        if (itemTypes.includes('holdings') && itemTypes.includes('thesis')) {
            return "Based on the portfolio holdings and investment thesis provided above, analyze how well the current positions align with the stated investment strategy and pillars.";
        } else if (itemTypes.includes('trades')) {
            return "Based on the trading activity data provided above, analyze recent trades and review trade patterns.";
        } else if (itemTypes.includes('metrics')) {
            return "Based on the performance metrics data provided above, analyze portfolio performance over time.";
        } else {
            return "Based on the portfolio data provided above, provide a comprehensive analysis.";
        }
    }

    quickResearch(action) {
        const select = document.getElementById('ticker-select');
        const custom = document.getElementById('custom-ticker').value.trim().toUpperCase();
        const selected = Array.from(select.selectedOptions).map(opt => opt.value);
        const activeTickers = custom ? [...selected, custom] : selected;
        
        let prompt = '';
        
        switch (action) {
            case 'research':
                if (activeTickers.length === 1) {
                    prompt = `Research ${activeTickers[0]} - latest news and analysis`;
                } else {
                    prompt = `Research the following stocks: ${activeTickers.join(', ')}. Provide latest news for each.`;
                }
                break;
            case 'analyze':
                if (activeTickers.length === 1) {
                    prompt = `Analyze ${activeTickers[0]} stock - recent performance and outlook`;
                } else {
                    prompt = `Analyze and compare the outlooks for: ${activeTickers.join(', ')}`;
                }
                break;
            case 'compare':
                prompt = `Compare ${activeTickers.join(' and ')} stocks. Which is a better investment?`;
                break;
            case 'earnings':
                if (activeTickers.length === 1) {
                    prompt = `Find recent earnings news for ${activeTickers[0]}`;
                } else {
                    prompt = `Find recent earnings reports for: ${activeTickers.join(', ')}`;
                }
                break;
            case 'portfolio':
                prompt = this.generateDefaultPrompt();
                break;
            case 'market':
                prompt = "What's the latest stock market news today?";
                break;
            case 'sector':
                prompt = "What's happening in the stock market sectors today?";
                break;
        }
        
        if (prompt) {
            document.getElementById('suggested-prompt-area').classList.remove('hidden');
            document.getElementById('editable-prompt').value = prompt;
        }
    }

    saveModelPreference() {
        // Save model preference to user settings
        fetch('/api/settings/ai_model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: this.selectedModel })
        }).catch(err => console.error('Error saving model preference:', err));
    }

    updateUI() {
        document.getElementById('current-model').textContent = this.selectedModel;
        this.updateContextUI();
        
        // Load portfolio tickers for quick research
        if (this.selectedFund) {
            this.loadPortfolioTickers();
        }
    }

    async loadPortfolioTickers() {
        if (!this.selectedFund) return;
        
        try {
            // Fetch portfolio positions to get tickers
            const response = await fetch(`/api/portfolio?fund=${encodeURIComponent(this.selectedFund)}`);
            if (response.ok) {
                const data = await response.json();
                const tickers = data.positions?.map(pos => pos.ticker).filter(Boolean) || [];
                const select = document.getElementById('ticker-select');
                select.innerHTML = '';
                [...new Set(tickers)].sort().forEach(ticker => {
                    const option = document.createElement('option');
                    option.value = ticker;
                    option.textContent = ticker;
                    select.appendChild(option);
                });
            }
        } catch (err) {
            this.showError('Error loading portfolio tickers: ' + err.message);
        }
    }

    retryLastMessage() {
        // Find last user message
        const lastUserMsg = this.conversationHistory.filter(msg => msg.role === 'user').pop();
        if (!lastUserMsg) {
            this.showError('No previous message to retry');
            return;
        }

        // Remove last assistant message if it exists
        if (this.conversationHistory.length > 0 && 
            this.conversationHistory[this.conversationHistory.length - 1].role === 'assistant') {
            this.conversationHistory.pop();
            // Remove last message from UI
            const messagesDiv = document.getElementById('chat-messages');
            const lastMessage = messagesDiv.lastElementChild;
            if (lastMessage) {
                lastMessage.remove();
            }
        }

        // Hide retry button
        document.getElementById('retry-button-container').classList.add('hidden');

        // Re-send the last user message
        this.sendMessage(lastUserMsg.content);
    }

    async checkPortfolioNews() {
        if (!this.selectedFund) {
            this.showError('Please select a fund first');
            return;
        }

        try {
            const response = await fetch('/api/v2/ai/portfolio-intelligence', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fund: this.selectedFund })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.matching_articles && data.matching_articles.length > 0) {
                // Format article context
                let articleContext = "Here are recent research articles found for the user's portfolio holdings:\n\n";
                data.matching_articles.slice(0, 10).forEach((art, i) => {
                    articleContext += `${i + 1}. Title: ${art.title}\n`;
                    articleContext += `   Holdings: ${art.matched_holdings.join(', ')}\n`;
                    articleContext += `   Summary: ${art.summary || 'No summary'}\n`;
                    articleContext += `   Conclusion: ${art.conclusion || 'N/A'}\n\n`;
                });

                const prompt = "Review the following recent research articles about my portfolio holdings. " +
                    "Identify any noteworthy events, risks, or opportunities that strictly require my attention.\n\n" +
                    articleContext;

                document.getElementById('suggested-prompt-area').classList.remove('hidden');
                document.getElementById('editable-prompt').value = prompt;
            } else {
                this.showError(`No recent articles found in the repository for your holdings (past 7 days).`);
            }
        } catch (err) {
            this.showError('Failed to check portfolio news: ' + err.message);
        }
    }

    showError(message) {
        // Show error in chat UI
        this.addMessage('assistant', `❌ Error: ${message}`);
    }

    updateRetryButton() {
        const retryContainer = document.getElementById('retry-button-container');
        if (this.conversationHistory.length > 0 && 
            this.conversationHistory[this.conversationHistory.length - 1].role === 'assistant') {
            retryContainer.classList.remove('hidden');
        } else {
            retryContainer.classList.add('hidden');
        }
    }
}
