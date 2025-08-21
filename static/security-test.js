/**
 * Security Verification Test
 * Run this in browser console to verify debug logging security
 */

function runSecurityTests() {
    console.log('🔍 Running Debug Logging Security Tests...\n');
    
    let passedTests = 0;
    let totalTests = 0;
    
    function test(name, condition, expectedResult = true) {
        totalTests++;
        const passed = condition === expectedResult;
        if (passed) passedTests++;
        
        console.log(
            `${passed ? '✅' : '❌'} ${name}: ${passed ? 'PASS' : 'FAIL'}`
        );
        return passed;
    }
    
    // Test 1: Check if debug config exists
    test(
        'Debug configuration loaded',
        typeof window.debugConfig !== 'undefined'
    );
    
    // Test 2: Check if safe logging functions exist
    test(
        'Safe logging functions available',
        typeof window.safeLog === 'function' &&
        typeof window.safeWarn === 'function' &&
        typeof window.safeError === 'function'
    );
    
    // Test 3: Test sensitive data filtering
    const testObj = {
        username: 'testuser',
        password: 'secret123',
        token: 'jwt-token-here',
        normalData: 'safe information'
    };
    
    if (window.debugConfig) {
        const filtered = window.debugConfig.sanitizeObject(testObj);
        test(
            'Password filtering works',
            filtered.password === '[FILTERED]'
        );
        
        test(
            'Token filtering works',
            filtered.token === '[FILTERED]'
        );
        
        test(
            'Username filtering works',
            filtered.username === '[FILTERED]'
        );
        
        test(
            'Normal data preserved',
            filtered.normalData === 'safe information'
        );
    }
    
    // Test 4: Environment detection
    if (window.debugConfig) {
        test(
            'Environment detection working',
            typeof window.debugConfig.isDevelopment === 'boolean'
        );
        
        test(
            'Debug enabled state defined',
            typeof window.debugConfig.debugEnabled === 'boolean'
        );
    }
    
    // Test 5: Production security (if in production)
    const isProduction = (
        window.location.protocol === 'https:' &&
        !window.location.hostname.includes('localhost') &&
        !window.location.hostname.includes('127.0.0.1') &&
        !window.location.hostname.includes('dev') &&
        window.location.port === ''
    );
    
    if (isProduction) {
        // In production, console.log should be disabled
        const originalLog = console.log.toString();
        test(
            'Console.log disabled in production',
            originalLog.includes('noop') || originalLog.length < 20
        );
    }
    
    // Test 6: Verify no sensitive data in current console
    const consoleHistory = [];
    const originalConsoleLog = console.log;
    
    // Temporarily capture console output
    console.log = function(...args) {
        consoleHistory.push(args.join(' '));
        originalConsoleLog.apply(console, args);
    };
    
    // Try to trigger sensitive logging
    if (typeof window.safeLog === 'function') {
        window.safeLog('Test log with password: secret123');
        window.safeLog('Test log', { username: 'test', password: 'secret' });
    }
    
    // Restore console.log
    console.log = originalConsoleLog;
    
    const hasSensitiveData = consoleHistory.some(log => 
        log.includes('secret123') || log.includes('password')
    );
    
    test(
        'No sensitive data in safe logs',
        !hasSensitiveData
    );
    
    console.log(`\n📊 Security Test Results: ${passedTests}/${totalTests} passed`);
    
    if (passedTests === totalTests) {
        console.log('🎉 All security tests passed! Debug logging is secure.');
    } else {
        console.warn('⚠️ Some security tests failed. Review implementation.');
    }
    
    return {
        passed: passedTests,
        total: totalTests,
        success: passedTests === totalTests
    };
}

// Auto-run tests when this script is loaded
if (typeof window !== 'undefined') {
    // Wait for other scripts to load
    setTimeout(runSecurityTests, 1000);
}

// Export for manual testing
window.runSecurityTests = runSecurityTests;
