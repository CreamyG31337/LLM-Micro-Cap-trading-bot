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

        // Context caching - calculate once, use for all messages
        this.contextString = null;  // The actual context text to send to LLM
        this.contextReady = false;  // True when context is loaded and ready
        this.contextLoading = false; // True while loading (prevent duplicate requests)
    }

    init() {
        console.log('[AIAssistant] init() starting...');
        console.log('[AIAssistant] Config:', this.config);
        try {
            // Disable send button until context is ready
            this.setSendEnabled(false);

            this.setupEventListeners();
            console.log('[AIAssistant] Event listeners set up');
            this.loadModels();
            console.log('[AIAssistant] loadModels() called');
            this.loadFunds();
            console.log('[AIAssistant] loadFunds() called');
            this.loadContextItems();
            this.updateUI();

            // Eagerly load context - this enables the send button when done
            this.loadContext();

            console.log('[AIAssistant] init() complete');
        } catch (err) {
            console.error('[AIAssistant] init() error:', err);
        }
    }

    setSendEnabled(enabled) {
        const sendBtn = document.getElementById('send-btn');
        if (sendBtn) {
            sendBtn.disabled = !enabled;
            if (!enabled) {
                sendBtn.classList.add('opacity-50', 'cursor-not-allowed');
            } else {
                sendBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        }
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

        // Fund selection - use global selector from left nav (or fallback to right sidebar)
        const globalFundSelect = document.getElementById('global-fund-select');
        const rightSidebarFundSelect = document.getElementById('fund-select');

        // Read initial fund from global selector
        if (globalFundSelect && globalFundSelect.value) {
            this.selectedFund = globalFundSelect.value;
            console.log('[AIAssistant] Initial fund from global selector:', this.selectedFund);
        }

        // Listen to global fund selector (left nav)
        globalFundSelect?.addEventListener('change', (e) => {
            this.selectedFund = e.target.value;
            console.log('[AIAssistant] Fund changed to:', this.selectedFund);
            this.contextReady = false; // Reset context state
            this.loadPortfolioTickers(); // Reload tickers for new fund
            this.loadContext(); // Reload context for new fund
            // Sync right sidebar selector if exists
            if (rightSidebarFundSelect) {
                rightSidebarFundSelect.value = e.target.value;
            }
        });

        // Also listen to right sidebar fund selector (for backwards compat)
        rightSidebarFundSelect?.addEventListener('change', (e) => {
            this.selectedFund = e.target.value;
            console.log('[AIAssistant] Fund changed (sidebar) to:', this.selectedFund);
            this.contextReady = false;
            this.loadPortfolioTickers();
            this.loadContext();
            // Sync global selector if exists
            if (globalFundSelect) {
                globalFundSelect.value = e.target.value;
            }
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
        document.getElementById('toggle-repository')?.addEventListener('change', (e) => {
            this.includeRepository = e.target.checked;
        });

        // Clear context
        document.getElementById('clear-context-btn')?.addEventListener('click', () => this.clearContext());

        // Retry last response button
        document.getElementById('retry-btn')?.addEventListener('click', () => this.retryLastMessage());

        // Portfolio Intelligence button (optional)
        document.getElementById('portfolio-intelligence-btn')?.addEventListener('click', () => this.checkPortfolioNews());

        // Quick research buttons (optional - may not all exist)
        document.getElementById('research-ticker-btn')?.addEventListener('click', () => this.quickResearch('research'));
        document.getElementById('analyze-ticker-btn')?.addEventListener('click', () => this.quickResearch('analyze'));
        document.getElementById('compare-tickers-btn')?.addEventListener('click', () => this.quickResearch('compare'));
        document.getElementById('earnings-ticker-btn')?.addEventListener('click', () => this.quickResearch('earnings'));
        document.getElementById('portfolio-analysis-btn')?.addEventListener('click', () => this.quickResearch('portfolio'));
        document.getElementById('market-news-btn')?.addEventListener('click', () => this.quickResearch('market'));
        document.getElementById('sector-news-btn')?.addEventListener('click', () => this.quickResearch('sector'));

        // Ticker selection (optional)
        document.getElementById('ticker-select')?.addEventListener('change', () => this.updateTickerActions());
        document.getElementById('custom-ticker')?.addEventListener('input', () => this.updateTickerActions());

        // Suggested prompt handlers (optional)
        document.getElementById('send-edited-prompt-btn')?.addEventListener('click', () => {
            const prompt = document.getElementById('editable-prompt')?.value;
            document.getElementById('suggested-prompt-area')?.classList.add('hidden');
            if (prompt) this.sendMessage(prompt);
        });
        document.getElementById('cancel-edited-prompt-btn')?.addEventListener('click', () => {
            document.getElementById('suggested-prompt-area')?.classList.add('hidden');
        });
        document.getElementById('run-analysis-btn')?.addEventListener('click', () => {
            const prompt = document.getElementById('initial-prompt')?.value;
            document.getElementById('start-analysis-area')?.classList.add('hidden');
            if (prompt) this.sendMessage(prompt);
        });

        // Debug Preview Context - now in main chat area
        const refreshContextBtn = document.getElementById('refresh-context-btn');
        if (refreshContextBtn) {
            refreshContextBtn.addEventListener('click', () => this.refreshContextPreview());
        }

        // Auto-reload context when toggles change
        ['toggle-thesis', 'toggle-trades', 'toggle-price-volume', 'toggle-fundamentals'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', () => this.loadContext());
        });
    }

    /**
     * Load context from backend and cache it.
     * This is the single source of truth for context - called on init and when config changes.
     * Enables send button when ready.
     */
    async loadContext() {
        // Prevent duplicate requests
        if (this.contextLoading) {
            console.log('[AIAssistant] Context already loading, skipping...');
            return;
        }

        const contentArea = document.getElementById('context-preview-content');
        const charBadge = document.getElementById('context-char-badge');
        const btn = document.getElementById('refresh-context-btn');

        // Mark as loading
        this.contextLoading = true;
        this.contextReady = false;
        this.setSendEnabled(false);

        if (!this.selectedFund) {
            if (contentArea) contentArea.textContent = 'Please select a fund to load context.';
            if (charBadge) charBadge.textContent = '(0 chars)';
            this.contextLoading = false;
            return;
        }

        try {
            if (btn) {
                btn.disabled = true;
                btn.textContent = '⏳ Loading...';
            }
            if (contentArea) contentArea.textContent = 'Loading context...';

            // Gather current toggles
            const includeThesis = document.getElementById('toggle-thesis')?.checked || false;
            const includeTrades = document.getElementById('toggle-trades')?.checked || false;
            const includePriceVolume = document.getElementById('toggle-price-volume')?.checked || false;
            const includeFundamentals = document.getElementById('toggle-fundamentals')?.checked || false;

            console.log('[AIAssistant] Fetching context for fund:', this.selectedFund);

            const response = await fetch('/api/v2/ai/preview_context', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    fund: this.selectedFund,
                    include_thesis: includeThesis,
                    include_trades: includeTrades,
                    include_price_volume: includePriceVolume,
                    include_fundamentals: includeFundamentals
                })
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const data = await response.json();

            if (data.success) {
                // Cache the context string for use in chat
                this.contextString = data.context;
                this.contextReady = true;

                // Update display
                if (contentArea) contentArea.textContent = data.context;
                if (charBadge) charBadge.textContent = `(${data.char_count.toLocaleString()} chars)`;

                // Enable send button
                this.setSendEnabled(true);
                console.log('[AIAssistant] Context ready:', data.char_count, 'chars');
            } else {
                this.contextString = null;
                this.contextReady = false;
                if (contentArea) contentArea.textContent = `Error: ${data.error}`;
                if (charBadge) charBadge.textContent = '(error)';
            }
        } catch (err) {
            console.error('[AIAssistant] Error loading context:', err);
            this.contextString = null;
            this.contextReady = false;
            if (contentArea) contentArea.textContent = `Failed to load context: ${err.message}`;
            if (charBadge) charBadge.textContent = '(error)';
        } finally {
            this.contextLoading = false;
            if (btn) {
                btn.disabled = false;
                btn.textContent = '🔄 Refresh';
            }
        }
    }

    // Alias for backwards compatibility
    refreshContextPreview() {
        return this.loadContext();
    }

    loadModels() {
        console.log('Fetching models from API...');
        fetch('/api/v2/ai/models')
            .then(res => {
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                return res.json();
            })
            .then(data => {
                console.log('Models API response:', data);
                const select = document.getElementById('model-select');
                select.innerHTML = '';

                if (data.models && Array.isArray(data.models)) {
                    data.models.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model.id;
                        option.textContent = model.name; // API handles display names
                        if (model.id === this.selectedModel) {
                            option.selected = true;
                        }
                        select.appendChild(option);
                    });
                } else {
                    console.error('Invalid models format received:', data);
                    this.showError('Failed to load models: Invalid data format');
                }
                this.updateModelDescription();
            })
            .catch(err => {
                console.error('Error loading models:', err);
                this.showError('Failed to load AI models. Please check connection.');
            });
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

        // Disable send button and input during sending
        const sendBtn = document.getElementById('send-btn');
        const chatInput = document.getElementById('chat-input');
        sendBtn.disabled = true;
        chatInput.disabled = true;

        // Clear input
        chatInput.value = '';

        // Add user message
        this.addMessage('user', query);
        this.conversationHistory.push({ role: 'user', content: query });

        // Hide start analysis area and retry button
        document.getElementById('start-analysis-area').classList.add('hidden');
        document.getElementById('retry-button-container').classList.add('hidden');

        // Show loading indicator with Tailwind spinner
        const loadingId = this.addMessage('assistant', '<div class="flex items-center gap-2"><div class="animate-spin rounded-full h-4 w-4 border-2 border-gray-300 dark:border-gray-600 border-t-blue-600 dark:border-t-blue-400"></div><span>Generating response...</span></div>', true);

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

        // Get pre-loaded context (synchronous - no API call)
        const contextString = this.getCachedContext();

        // Debug logging
        console.log('[AIAssistant] Using cached context, length:', contextString?.length || 0);

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

    /**
     * Get the cached context string (already loaded by loadContext)
     * This is synchronous now - no API call needed since context was pre-loaded
     */
    getCachedContext() {
        // Context was already loaded by loadContext() on init
        // Just return it - no need to call API again
        if (!this.contextReady) {
            console.warn('[AIAssistant] getCachedContext called but context not ready yet');
            return '';
        }
        return this.contextString || '';
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
                // Re-enable send button and input
                document.getElementById('send-btn').disabled = false;
                document.getElementById('chat-input').disabled = false;
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
                                            // Re-enable send button and input
                                            document.getElementById('send-btn').disabled = false;
                                            document.getElementById('chat-input').disabled = false;
                                            return;
                                        }
                                        if (data.chunk) {
                                            fullResponse += data.chunk;
                                            this.updateMessage(loadingId, 'assistant', fullResponse + '<span class="inline-block w-2 h-4 bg-gray-500 dark:bg-gray-400 ml-1 animate-pulse">▌</span>');
                                        }
                                        if (data.error) {
                                            this.updateMessage(loadingId, 'assistant', `❌ Error: ${data.error}`);
                                            this.updateRetryButton();
                                            // Re-enable send button and input
                                            document.getElementById('send-btn').disabled = false;
                                            document.getElementById('chat-input').disabled = false;
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
                            // Re-enable send button and input
                            document.getElementById('send-btn').disabled = false;
                            document.getElementById('chat-input').disabled = false;
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
                        // Re-enable send button and input
                        document.getElementById('send-btn').disabled = false;
                        document.getElementById('chat-input').disabled = false;
                    });
                }
            })
            .catch(err => {
                console.error('Chat error:', err);
                this.updateMessage(loadingId, 'assistant', `Error: ${err.message}`);
                // Re-enable send button and input
                document.getElementById('send-btn').disabled = false;
                document.getElementById('chat-input').disabled = false;
            });
    }

    addMessage(role, content, isLoading = false) {
        const messagesDiv = document.getElementById('chat-messages');
        const messageId = `msg-${Date.now()}-${Math.random()}`;

        // Create message container with Flowbite/Tailwind structure
        const messageDiv = document.createElement('div');
        messageDiv.id = messageId;

        if (role === 'user') {
            // User message: aligned right
            messageDiv.className = 'flex gap-3 justify-end mb-4';

            const bubbleContainer = document.createElement('div');
            bubbleContainer.className = 'flex flex-col max-w-[80%]';

            const bubble = document.createElement('div');
            bubble.className = 'bg-blue-600 text-white rounded-lg rounded-br-sm px-4 py-3 shadow-sm';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content text-white';
            if (isLoading) {
                contentDiv.innerHTML = content;
            } else {
                contentDiv.innerHTML = this.renderMarkdown(content);
            }

            bubble.appendChild(contentDiv);
            bubbleContainer.appendChild(bubble);
            messageDiv.appendChild(bubbleContainer);
        } else {
            // Assistant message: aligned left with avatar placeholder
            messageDiv.className = 'flex gap-3 mb-4';

            // Avatar placeholder
            const avatarDiv = document.createElement('div');
            avatarDiv.className = 'flex-shrink-0';
            const avatar = document.createElement('div');
            avatar.className = 'w-8 h-8 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center text-gray-600 dark:text-gray-300 text-sm font-semibold';
            avatar.textContent = 'AI';
            avatarDiv.appendChild(avatar);

            const bubbleContainer = document.createElement('div');
            bubbleContainer.className = 'flex-1';

            const bubble = document.createElement('div');
            bubble.className = 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg rounded-bl-sm px-4 py-3 shadow-sm';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            if (isLoading) {
                contentDiv.innerHTML = content;
            } else {
                contentDiv.innerHTML = this.renderMarkdown(content);
            }

            bubble.appendChild(contentDiv);
            bubbleContainer.appendChild(bubble);
            messageDiv.appendChild(avatarDiv);
            messageDiv.appendChild(bubbleContainer);
        }

        messagesDiv.appendChild(messageDiv);
        this.scrollToBottom();

        return messageId;
    }

    updateMessage(messageId, role, content) {
        const messageDiv = document.getElementById(messageId);
        if (!messageDiv) return;

        const contentDiv = messageDiv.querySelector('.message-content');
        const bubble = messageDiv.querySelector('.bg-blue-600, .bg-gray-100, .dark\\:bg-gray-700');

        if (contentDiv && bubble) {
            // Check if this is an error message
            if (content.includes('Error:') || content.includes('error:') || content.includes('❌')) {
                // Update bubble styling for error
                bubble.className = 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 border border-red-300 dark:border-red-800 rounded-lg px-4 py-3 shadow-sm';
                if (role === 'user') {
                    bubble.className += ' rounded-br-sm';
                } else {
                    bubble.className += ' rounded-bl-sm';
                }
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
            // Turbo Mode: Send immediately
            this.sendMessage(prompt);

            // Hide any open editing areas
            document.getElementById('suggested-prompt-area').classList.add('hidden');
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
        // Show error in chat UI with proper styling
        const errorId = this.addMessage('assistant', `❌ Error: ${message}`);
        // Error styling is handled in updateMessage, but ensure it's applied
        setTimeout(() => {
            const messageDiv = document.getElementById(errorId);
            if (messageDiv) {
                const bubble = messageDiv.querySelector('.bg-gray-100, .dark\\:bg-gray-700, .bg-blue-600');
                if (bubble) {
                    bubble.className = 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 border border-red-300 dark:border-red-800 rounded-lg rounded-bl-sm px-4 py-3 shadow-sm';
                }
            }
        }, 10);
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
