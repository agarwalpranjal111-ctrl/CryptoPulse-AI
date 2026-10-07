/**
 * WebSocket functionality for real-time price feeds
 * Blockchain Analytics Dashboard
 */

// Initialize native WebSocket connection
let socket;
let isConnected = false;
let subscribedCoins = new Set();
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
const reconnectDelay = 3000; // 3 seconds

// Initialize WebSocket connection
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    try {
        socket = new WebSocket(wsUrl);
        
        socket.onopen = function() {
            console.log('Connected to WebSocket server');
            isConnected = true;
            reconnectAttempts = 0;
            updateConnectionStatus(true);
            
            // Show connection notification
            if (typeof showNotification === 'function') {
                showNotification('Connected to live price feeds', 'success', 3000);
            }
        };
        
        socket.onclose = function() {
            console.log('Disconnected from WebSocket server');
            isConnected = false;
            updateConnectionStatus(false);
            
            // Show disconnection notification
            if (typeof showNotification === 'function') {
                showNotification('Disconnected from live feeds', 'warning', 3000);
            }
            
            // Attempt to reconnect
            if (reconnectAttempts < maxReconnectAttempts) {
                setTimeout(() => {
                    reconnectAttempts++;
                    console.log(`Attempting to reconnect... (${reconnectAttempts}/${maxReconnectAttempts})`);
                    initWebSocket();
                }, reconnectDelay);
            }
        };
        
        socket.onerror = function(error) {
            console.error('WebSocket error:', error);
        };
        
        socket.onmessage = function(event) {
            try {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
        
    } catch (error) {
        console.error('Failed to initialize WebSocket:', error);
    }
}

// Handle incoming WebSocket messages
function handleWebSocketMessage(message) {
    const { type, data } = message;
    
    switch (type) {
        case 'status':
            console.log('Server status:', data.msg);
            break;
            
        case 'price_update':
            console.log('Received price update:', data);
            try {
                // Update market overview if on dashboard page
                if (window.location.pathname === '/' || window.location.pathname === '/dashboard') {
                    updateMarketDataReal(data);
                }
                
                // Update any price displays with animation
                updatePriceDisplays(data.coins);
                
                // Update last updated timestamp
                updateLastUpdatedTime();
                
            } catch (error) {
                console.error('Error processing price update:', error);
            }
            break;
            
        case 'trending_update':
            console.log('Received trending update:', data);
            try {
                // Update trending coins if on dashboard page
                if (window.location.pathname === '/' || window.location.pathname === '/dashboard') {
                    updateTrendingCoinsReal(data.trending);
                }
            } catch (error) {
                console.error('Error processing trending update:', error);
            }
            break;
            
        case 'live_price_response':
            console.log('Received live price response:', data);
            updateSingleCoinPrice(data);
            break;
            
        case 'live_price_error':
            console.error('Live price error:', data.error);
            if (typeof showNotification === 'function') {
                showNotification(`Price update error: ${data.error}`, 'danger');
            }
            break;
            
        case 'subscription_confirmed':
            console.log('Subscription confirmed for:', data.coin_id);
            subscribedCoins.add(data.coin_id);
            if (typeof showNotification === 'function') {
                showNotification(`Subscribed to ${data.coin_id} live updates`, 'info', 2000);
            }
            break;
            
        default:
            console.log('Unknown message type:', type, data);
    }
}

// Send message to WebSocket server
function sendWebSocketMessage(type, data) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        const message = JSON.stringify({ type, data });
        socket.send(message);
    } else {
        console.warn('WebSocket is not connected. Cannot send message:', type, data);
    }
}

// WebSocket utility functions
function updateConnectionStatus(connected) {
    const statusElements = document.querySelectorAll('.connection-status');
    statusElements.forEach(element => {
        element.className = `badge ${connected ? 'bg-success' : 'bg-danger'}`;
        element.textContent = connected ? 'Live' : 'Offline';
    });
    
    // Update any live indicators
    const liveIndicators = document.querySelectorAll('#lastUpdated, .live-status');
    liveIndicators.forEach(element => {
        if (connected) {
            element.className = element.className.replace('bg-danger', 'bg-success');
            element.textContent = 'Live';
        } else {
            element.className = element.className.replace('bg-success', 'bg-danger');
            element.textContent = 'Offline';
        }
    });
}

function updateMarketDataReal(marketData) {
    if (!marketData || !marketData.global) return;
    
    const global = marketData.global;
    
    // Update market stats with animation
    animateNumberUpdate('totalMarketCap', global.total_market_cap?.usd, formatCurrency);
    animateNumberUpdate('totalVolume', global.total_volume?.usd, formatCurrency);
    animateNumberUpdate('btcDominance', global.market_cap_percentage?.btc, (val) => val?.toFixed(1) + '%');
    animateNumberUpdate('activeCryptos', global.active_cryptocurrencies, formatNumber);
    
    // Update crypto table if it exists
    if (marketData.coins && typeof updateCryptoTable === 'function') {
        updateCryptoTable(marketData.coins);
    }
}

function updateTrendingCoinsReal(trendingData) {
    if (!trendingData || typeof updateTrendingCoins !== 'function') return;
    updateTrendingCoins(trendingData);
}

function updatePriceDisplays(coins) {
    if (!coins || !Array.isArray(coins)) return;
    
    coins.forEach(coin => {
        // Update any elements showing this coin's price
        const priceElements = document.querySelectorAll(`[data-coin="${coin.id}"] .price`);
        priceElements.forEach(element => {
            const oldPrice = parseFloat(element.dataset.price || 0);
            const newPrice = coin.current_price;
            
            if (oldPrice !== newPrice) {
                // Add price change animation
                element.classList.remove('price-up', 'price-down');
                element.classList.add(newPrice > oldPrice ? 'price-up' : 'price-down');
                
                // Update price value
                element.textContent = `$${newPrice.toFixed(newPrice < 1 ? 6 : 2)}`;
                element.dataset.price = newPrice;
                
                // Remove animation class after animation completes
                setTimeout(() => {
                    element.classList.remove('price-up', 'price-down');
                }, 500);
            }
        });
        
        // Update percentage changes
        const changeElements = document.querySelectorAll(`[data-coin="${coin.id}"] .change-24h`);
        changeElements.forEach(element => {
            const change = coin.price_change_percentage_24h;
            element.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
            element.className = `badge ${change >= 0 ? 'bg-success' : 'bg-danger'}`;
        });
    });
}

function updateSingleCoinPrice(priceData) {
    const coinId = priceData.coin_id;
    const price = priceData.price;
    const change = priceData.change_24h;
    
    // Update any specific coin price displays
    const coinElements = document.querySelectorAll(`[data-coin="${coinId}"]`);
    coinElements.forEach(element => {
        const priceElement = element.querySelector('.current-price, .price');
        const changeElement = element.querySelector('.price-change, .change');
        
        if (priceElement) {
            const oldPrice = parseFloat(priceElement.dataset.price || 0);
            priceElement.textContent = `$${price.toFixed(price < 1 ? 6 : 2)}`;
            priceElement.dataset.price = price;
            
            // Add animation
            if (oldPrice !== price) {
                priceElement.classList.remove('price-up', 'price-down');
                priceElement.classList.add(price > oldPrice ? 'price-up' : 'price-down');
                setTimeout(() => priceElement.classList.remove('price-up', 'price-down'), 500);
            }
        }
        
        if (changeElement) {
            changeElement.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
            changeElement.className = `badge ${change >= 0 ? 'bg-success' : 'bg-danger'}`;
        }
    });
}

function animateNumberUpdate(elementId, newValue, formatter) {
    const element = document.getElementById(elementId);
    if (!element || newValue === undefined || newValue === null) return;
    
    const currentText = element.textContent;
    const currentValue = parseFloat(currentText.replace(/[^0-9.-]/g, '')) || 0;
    
    if (currentValue !== newValue && typeof animateNumber === 'function') {
        animateNumber(element, currentValue, newValue, 1000, formatter);
    } else if (formatter) {
        element.textContent = formatter(newValue);
    } else {
        element.textContent = newValue.toLocaleString();
    }
}

function updateLastUpdatedTime() {
    const timestampElements = document.querySelectorAll('#lastUpdated, .last-updated');
    timestampElements.forEach(element => {
        if (isConnected) {
            element.textContent = 'Live';
            element.className = element.className.replace('bg-secondary', 'bg-success');
        }
    });
}

// Public API functions
window.WebSocketAPI = {
    // Subscribe to specific coin updates
    subscribeToCoin: function(coinId) {
        if (isConnected && coinId) {
            sendWebSocketMessage('subscribe_to_coin', { coin_id: coinId });
            console.log(`Subscribing to ${coinId} updates`);
        }
    },
    
    // Request immediate price data for a coin
    requestLivePrice: function(coinId) {
        if (isConnected) {
            sendWebSocketMessage('get_live_price', { coin_id: coinId || 'bitcoin' });
        }
    },
    
    // Check connection status
    isConnected: function() {
        return isConnected;
    },
    
    // Get list of subscribed coins
    getSubscribedCoins: function() {
        return Array.from(subscribedCoins);
    },
    
    // Manually trigger connection
    connect: function() {
        if (!isConnected) {
            initWebSocket();
        }
    },
    
    // Manually disconnect
    disconnect: function() {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.close();
        }
    }
};

// Initialize WebSocket connection when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize WebSocket connection
    initWebSocket();
    
    // Wait a bit for the connection to establish, then auto-subscribe
    setTimeout(() => {
        if (isConnected) {
            const pathname = window.location.pathname;
            
            if (pathname === '/' || pathname === '/dashboard') {
                // Subscribe to top coins for dashboard
                const topCoins = ['bitcoin', 'ethereum', 'binancecoin', 'cardano', 'solana'];
                topCoins.forEach(coin => WebSocketAPI.subscribeToCoin(coin));
            } else if (pathname.includes('predictions') || pathname.includes('patterns')) {
                // Subscribe based on selected coin in dropdowns
                const coinSelect = document.getElementById('coinSelect');
                if (coinSelect && coinSelect.value) {
                    WebSocketAPI.subscribeToCoin(coinSelect.value);
                    
                    // Subscribe when selection changes
                    coinSelect.addEventListener('change', function() {
                        WebSocketAPI.subscribeToCoin(this.value);
                    });
                }
            }
        }
    }, 2000);
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
    }
});

console.log('WebSocket client initialized');