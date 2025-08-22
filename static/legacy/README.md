# Legacy and Debug HTML Files

This directory contains legacy and debug HTML variants that are no longer actively used in production.

## Legacy Interface Files
- **`index-clean.html`** - Clean version of main interface without accessibility features
- **`simple.html`** - Simplified chat interface with minimal features
- **`simple-clean.html`** - Duplicate of simple.html
- **`simple.css`** - Stylesheet for simple interfaces
- **`simple-handlers.js`** - JavaScript handlers for simple interfaces

## Debug/Test Files
- **`debug.html`** - Login diagnostics and error detection interface
- **`debug-clean.html`** - Clean debug version
- **`debug.css`** - Stylesheet for debug interfaces
- **`debug-handlers.js`** - JavaScript handlers for debug interfaces
- **`test.html`** - Login test interface with detailed debug information
- **`test-history.html`** - History API testing interface
- **`history-debug.html`** - Empty debug file (can be removed)

## Purpose
These files were moved here to reduce maintenance overhead while preserving them for:
- Development debugging
- Feature testing
- Historical reference
- Potential future use

## Production Files
The main production interface is now only:
- **`../index.html`** - Main production interface (full featured)
- **`../docs.html`** - API documentation interface

## Usage
If you need to use any of these files for debugging:
1. Copy the desired file back to the parent `static/` directory
2. Modify server routing if needed
3. Remember to move it back here when done

## Cleanup Notes
- All `.backup` files have been removed
- Only actively maintained production files remain in the main static directory
- This organization reduces confusion and maintenance burden
