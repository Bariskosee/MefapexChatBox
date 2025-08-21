/**
 * Debug Configuration Manager
 * Controls debug logging based on environment and development flags
 */

class DebugConfig {
    constructor() {
        this.isDevelopment = this.checkDevelopmentMode();
        this.debugEnabled = this.isDevelopment && this.isDebugEnabled();
        this.allowSensitiveLogs = false; // Never allow sensitive logs in any environment
        
        // Initialize debug level
        this.initializeDebugLevel();
        
        console.log(`🔧 Debug Config: Development=${this.isDevelopment}, Debug=${this.debugEnabled}`);
    }
    
    checkDevelopmentMode() {
        // Check multiple indicators for development mode
        return (
            window.location.hostname === 'localhost' ||
            window.location.hostname === '127.0.0.1' ||
            window.location.hostname.includes('dev') ||
            window.location.port !== '' ||
            localStorage.getItem('debug_mode') === 'true'
        );
    }
    
    isDebugEnabled() {
        // Check URL parameters and local storage for debug flags
        const urlParams = new URLSearchParams(window.location.search);
        return (
            urlParams.get('debug') === 'true' ||
            localStorage.getItem('debug_enabled') === 'true' ||
            sessionStorage.getItem('debug_enabled') === 'true'
        );
    }
    
    initializeDebugLevel() {
        if (!this.debugEnabled) {
            // In production, override console methods to prevent any debug output
            this.disableDebugLogging();
        }
    }
    
    disableDebugLogging() {
        // Create safe console methods that filter sensitive information
        const originalLog = console.log;
        const originalWarn = console.warn;
        const originalError = console.error;
        
        console.log = (...args) => {
            if (this.debugEnabled && !this.containsSensitiveData(args)) {
                originalLog.apply(console, args);
            }
        };
        
        console.warn = (...args) => {
            if (this.debugEnabled && !this.containsSensitiveData(args)) {
                originalWarn.apply(console, args);
            }
        };
        
        console.error = (...args) => {
            // Always allow error logs, but filter sensitive data
            const filteredArgs = this.filterSensitiveData(args);
            originalError.apply(console, filteredArgs);
        };
    }
    
    containsSensitiveData(args) {
        const sensitiveKeywords = [
            'password', 'token', 'auth', 'credential', 'secret',
            'key', 'session', 'cookie', 'jwt', 'bearer'
        ];
        
        return args.some(arg => {
            if (typeof arg === 'string') {
                return sensitiveKeywords.some(keyword => 
                    arg.toLowerCase().includes(keyword)
                );
            }
            if (typeof arg === 'object' && arg !== null) {
                return this.objectContainsSensitiveData(arg);
            }
            return false;
        });
    }
    
    objectContainsSensitiveData(obj) {
        const sensitiveFields = [
            'password', 'token', 'access_token', 'refresh_token',
            'authorization', 'auth', 'credential', 'secret',
            'key', 'session_id', 'sessionId'
        ];
        
        if (Array.isArray(obj)) {
            return obj.some(item => this.objectContainsSensitiveData(item));
        }
        
        return Object.keys(obj).some(key => 
            sensitiveFields.includes(key.toLowerCase())
        );
    }
    
    filterSensitiveData(args) {
        return args.map(arg => {
            if (typeof arg === 'object' && arg !== null) {
                return this.sanitizeObject(arg);
            }
            if (typeof arg === 'string' && this.containsSensitiveData([arg])) {
                return '[FILTERED]';
            }
            return arg;
        });
    }
    
    sanitizeObject(obj) {
        if (Array.isArray(obj)) {
            return obj.map(item => this.sanitizeObject(item));
        }
        
        const sanitized = {};
        for (const [key, value] of Object.entries(obj)) {
            if (this.isSensitiveField(key)) {
                sanitized[key] = '[FILTERED]';
            } else if (typeof value === 'object' && value !== null) {
                sanitized[key] = this.sanitizeObject(value);
            } else {
                sanitized[key] = value;
            }
        }
        return sanitized;
    }
    
    isSensitiveField(fieldName) {
        const sensitiveFields = [
            'password', 'token', 'access_token', 'refresh_token',
            'authorization', 'auth', 'credential', 'secret',
            'key', 'session_id', 'sessionId', 'jwt'
        ];
        return sensitiveFields.includes(fieldName.toLowerCase());
    }
    
    // Safe logging methods
    safeLog(message, data = null) {
        if (this.debugEnabled) {
            if (data) {
                console.log(message, this.sanitizeObject(data));
            } else {
                console.log(message);
            }
        }
    }
    
    safeWarn(message, data = null) {
        if (this.debugEnabled) {
            if (data) {
                console.warn(message, this.sanitizeObject(data));
            } else {
                console.warn(message);
            }
        }
    }
    
    safeError(message, data = null) {
        // Always log errors, but sanitize data
        if (data) {
            console.error(message, this.sanitizeObject(data));
        } else {
            console.error(message);
        }
    }
    
    // Development-only logging
    devLog(message, data = null) {
        if (this.isDevelopment && this.debugEnabled) {
            if (data) {
                console.log(`[DEV] ${message}`, this.sanitizeObject(data));
            } else {
                console.log(`[DEV] ${message}`);
            }
        }
    }
    
    // Enable/disable debug mode
    enableDebug() {
        this.debugEnabled = true;
        localStorage.setItem('debug_enabled', 'true');
        console.log('🔧 Debug mode enabled');
    }
    
    disableDebug() {
        this.debugEnabled = false;
        localStorage.removeItem('debug_enabled');
        console.log('🔧 Debug mode disabled');
    }
}

// Global debug configuration instance
window.debugConfig = new DebugConfig();

// Expose safe logging methods globally
window.safeLog = (...args) => window.debugConfig.safeLog(...args);
window.safeWarn = (...args) => window.debugConfig.safeWarn(...args);
window.safeError = (...args) => window.debugConfig.safeError(...args);
window.devLog = (...args) => window.debugConfig.devLog(...args);

console.log('🛡️ Debug configuration loaded - sensitive data protection enabled');
