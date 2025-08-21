/**
 * Production Security Configuration
 * This file ensures that all debug information is properly secured in production
 */

// Production security checks
(function() {
    'use strict';
    
    // Check if we're in production environment
    const isProduction = (
        window.location.protocol === 'https:' &&
        !window.location.hostname.includes('localhost') &&
        !window.location.hostname.includes('127.0.0.1') &&
        !window.location.hostname.includes('dev') &&
        window.location.port === ''
    );
    
    if (isProduction) {
        // In production, completely disable console logging
        const noop = function() {};
        
        // Preserve only error logging for debugging production issues
        const originalError = console.error;
        const originalWarn = console.warn;
        
        // Override all console methods
        console.log = noop;
        console.info = noop;
        console.debug = noop;
        console.trace = noop;
        console.dir = noop;
        console.dirxml = noop;
        console.group = noop;
        console.groupCollapsed = noop;
        console.groupEnd = noop;
        console.time = noop;
        console.timeEnd = noop;
        console.count = noop;
        console.clear = noop;
        
        // Filter sensitive data from errors and warnings
        console.error = function(...args) {
            const filteredArgs = args.map(arg => {
                if (typeof arg === 'string' && containsSensitiveKeywords(arg)) {
                    return '[FILTERED_SENSITIVE_DATA]';
                }
                if (typeof arg === 'object' && arg !== null) {
                    return filterSensitiveObject(arg);
                }
                return arg;
            });
            originalError.apply(console, filteredArgs);
        };
        
        console.warn = function(...args) {
            const filteredArgs = args.map(arg => {
                if (typeof arg === 'string' && containsSensitiveKeywords(arg)) {
                    return '[FILTERED_SENSITIVE_DATA]';
                }
                if (typeof arg === 'object' && arg !== null) {
                    return filterSensitiveObject(arg);
                }
                return arg;
            });
            originalWarn.apply(console, filteredArgs);
        };
        
        // Disable debugging tools
        if (typeof window.debugConfig !== 'undefined') {
            window.debugConfig.debugEnabled = false;
            window.debugConfig.isDevelopment = false;
        }
        
        // Override global debug functions
        window.safeLog = noop;
        window.devLog = noop;
        
        console.info('🔒 Production mode: Debug logging disabled');
    }
    
    function containsSensitiveKeywords(str) {
        const sensitiveKeywords = [
            'password', 'token', 'auth', 'credential', 'secret',
            'key', 'session', 'cookie', 'jwt', 'bearer', 'username'
        ];
        const lowerStr = str.toLowerCase();
        return sensitiveKeywords.some(keyword => lowerStr.includes(keyword));
    }
    
    function filterSensitiveObject(obj) {
        if (Array.isArray(obj)) {
            return obj.map(item => filterSensitiveObject(item));
        }
        
        if (typeof obj !== 'object' || obj === null) {
            return obj;
        }
        
        const filtered = {};
        const sensitiveFields = [
            'password', 'token', 'access_token', 'refresh_token',
            'authorization', 'auth', 'credential', 'secret',
            'key', 'session_id', 'sessionId', 'jwt', 'username'
        ];
        
        for (const [key, value] of Object.entries(obj)) {
            if (sensitiveFields.includes(key.toLowerCase())) {
                filtered[key] = '[FILTERED]';
            } else if (typeof value === 'object' && value !== null) {
                filtered[key] = filterSensitiveObject(value);
            } else {
                filtered[key] = value;
            }
        }
        
        return filtered;
    }
    
    // Prevent common debugging techniques
    if (isProduction) {
        // Disable right-click context menu in production
        document.addEventListener('contextmenu', function(e) {
            e.preventDefault();
        });
        
        // Disable F12, Ctrl+Shift+I, Ctrl+U shortcuts
        document.addEventListener('keydown', function(e) {
            if (
                e.keyCode === 123 || // F12
                (e.ctrlKey && e.shiftKey && e.keyCode === 73) || // Ctrl+Shift+I
                (e.ctrlKey && e.keyCode === 85) // Ctrl+U
            ) {
                e.preventDefault();
            }
        });
        
        // Detect developer tools
        let devtools = {
            open: false,
            orientation: null
        };
        
        setInterval(function() {
            if (window.outerHeight - window.innerHeight > 200 || 
                window.outerWidth - window.innerWidth > 200) {
                if (!devtools.open) {
                    devtools.open = true;
                    console.clear();
                    console.warn('🔒 Developer tools detected in production environment');
                }
            } else {
                devtools.open = false;
            }
        }, 500);
    }
    
})();

console.log('🛡️ Production security configuration loaded');
