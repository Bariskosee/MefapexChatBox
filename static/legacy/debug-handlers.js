// Debug page functionality
const API_BASE_URL = window.location.origin;

function log(message, type = 'info') {
    const debugLog = document.getElementById('debugLog');
    const timestamp = new Date().toLocaleTimeString();
    const prefix = type === 'error' ? '❌' : type === 'success' ? '✅' : type === 'warn' ? '⚠️' : 'ℹ️';
    debugLog.textContent += `[${timestamp}] ${prefix} ${message}\n`;
    debugLog.scrollTop = debugLog.scrollHeight;
    
    console.log(`[${timestamp}] ${message}`);
}

function setStatus(message, type = 'info') {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = `status ${type}`;
    status.style.display = 'block';
}

function clearLog() {
    document.getElementById('debugLog').textContent = '';
    document.getElementById('status').style.display = 'none';
    log('Debug log cleared');
}

async function testAPI() {
    log('Testing API connection...', 'info');
    setStatus('Testing API...', 'info');
    
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        
        log(`API Response: ${JSON.stringify(data, null, 2)}`, 'success');
        setStatus('✅ API is working!', 'success');
    } catch (error) {
        log(`API Error: ${error.message}`, 'error');
        setStatus('❌ API connection failed', 'error');
    }
}

async function testJWTLogin() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    // SECURITY: Don't log actual credentials
    log(`Testing JWT Login (credentials provided)`, 'info');
    setStatus('Testing JWT login...', 'info');
    
    try {
        const requestData = { username, password };
        log(`Request prepared for JWT login`, 'info');
        
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        log(`Response status: ${response.status} ${response.statusText}`, 'info');
        
        if (response.ok) {
            const data = await response.json();
            // SECURITY: Don't log full response data that may contain tokens
            log(`JWT Login Success (response received)`, 'success');
            setStatus('✅ JWT Login successful!', 'success');
            
            // Test the /me endpoint
            if (data.access_token) {
                await testMeEndpoint('[TOKEN_FILTERED]'); // Don't pass actual token to log
            }
        } else {
            const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
            log(`JWT Login Failed: ${JSON.stringify(errorData, null, 2)}`, 'error');
            setStatus('❌ JWT Login failed', 'error');
        }
    } catch (error) {
        log(`JWT Login Error: ${error.message}`, 'error');
        setStatus('💥 JWT Login error', 'error');
    }
}

async function testLegacyLogin() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    // SECURITY: Don't log actual credentials
    log(`Testing Legacy Login (credentials provided)`, 'info');
    setStatus('Testing legacy login...', 'info');
    
    try {
        const requestData = { username, password };
        log(`Request prepared for legacy login`, 'info');
        
        const response = await fetch(`${API_BASE_URL}/login-legacy`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        log(`Response status: ${response.status} ${response.statusText}`, 'info');
        
        const data = await response.json();
        log(`Legacy Login Response processed`, data.success ? 'success' : 'error');
        
        if (data.success) {
            setStatus('✅ Legacy Login successful!', 'success');
        } else {
            setStatus(`❌ Legacy Login failed: ${data.message}`, 'error');
        }
    } catch (error) {
        log(`Legacy Login Error: ${error.message}`, 'error');
        setStatus('💥 Legacy Login error', 'error');
    }
}

async function testMeEndpoint(token) {
    log('Testing /me endpoint...', 'info');
    
    try {
        const response = await fetch(`${API_BASE_URL}/me`, {
            headers: { 'Authorization': `Bearer [TOKEN_FILTERED]` } // Don't log actual token
        });
        
        if (response.ok) {
            const userData = await response.json();
            // SECURITY: Don't log full user data that may contain sensitive info
            log(`User Data received successfully`, 'success');
        } else {
            log(`/me endpoint failed: ${response.status}`, 'error');
        }
    } catch (error) {
        log(`/me endpoint error: ${error.message}`, 'error');
    }
}

async function testOriginalScript() {
    log('Testing Original Script Login Function...', 'info');
    setStatus('Testing original login...', 'info');
    
    try {
        // Check if original login function exists
        if (typeof window.login === 'function') {
            log('Original login function found, calling it...', 'info');
            await window.login();
        } else {
            log('Original login function not found, loading original script...', 'warn');
            
            // Try to load and execute the original login logic
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            // Simulate the original login process
            log('Simulating original login process...', 'info');
            
            // First try JWT
            const jwtResponse = await fetch(`${API_BASE_URL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            if (jwtResponse.ok) {
                const jwtData = await jwtResponse.json();
                log('JWT login successful in original simulation', 'success');
                
                // Check if session manager would work
                if (typeof window.sessionManager !== 'undefined') {
                    log('SessionManager found', 'success');
                } else {
                    log('SessionManager NOT found - this is likely the issue!', 'error');
                }
                
                setStatus('✅ Original logic would work (JWT)', 'success');
            } else {
                // Try legacy
                const legacyResponse = await fetch(`${API_BASE_URL}/login-legacy`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                
                const legacyData = await legacyResponse.json();
                if (legacyData.success) {
                    log('Legacy login successful in original simulation', 'success');
                    setStatus('✅ Original logic would work (Legacy)', 'success');
                } else {
                    log('Both JWT and Legacy failed in original simulation', 'error');
                    setStatus('❌ Original logic would fail', 'error');
                }
            }
        }
    } catch (error) {
        log(`Original script test error: ${error.message}`, 'error');
        setStatus('💥 Original script test failed', 'error');
    }
}

// Check for JavaScript errors
window.addEventListener('error', function(event) {
    log(`JavaScript Error: ${event.error.message} at ${event.filename}:${event.lineno}`, 'error');
});

window.addEventListener('unhandledrejection', function(event) {
    log(`Unhandled Promise Rejection: ${event.reason}`, 'error');
});

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    log('Debug page loaded', 'info');
    log(`API Base URL: ${API_BASE_URL}`, 'info');
    
    // Check if original scripts are loaded
    if (typeof window.sessionManager !== 'undefined') {
        log('SessionManager is available', 'success');
    } else {
        log('SessionManager is NOT available', 'warn');
    }
    
    if (typeof window.login === 'function') {
        log('Original login function is available', 'success');
    } else {
        log('Original login function is NOT available', 'warn');
    }
    
    // Setup button event listeners using data-action attributes
    document.querySelectorAll('button[data-action]').forEach(button => {
        const action = button.getAttribute('data-action');
        switch(action) {
            case 'testJWTLogin':
                button.addEventListener('click', testJWTLogin);
                break;
            case 'testLegacyLogin':
                button.addEventListener('click', testLegacyLogin);
                break;
            case 'testOriginalScript':
                button.addEventListener('click', testOriginalScript);
                break;
            case 'testAPI':
                button.addEventListener('click', testAPI);
                break;
            case 'clearLog':
                button.addEventListener('click', clearLog);
                break;
        }
    });
    
    // Auto-test API on load
    setTimeout(testAPI, 500);
    
    // Handle Enter key in password field
    const passwordField = document.getElementById('password');
    if (passwordField) {
        passwordField.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                testJWTLogin();
            }
        });
    }
});
