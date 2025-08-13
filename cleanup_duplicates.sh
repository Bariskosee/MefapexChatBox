#!/bin/bash

# 🧹 MEFAPEX Chatbot - Cleanup Script
# This script removes duplicate backup files after successful unification

echo "🧹 MEFAPEX Chatbot Cleanup Script"
echo "=================================="
echo ""

# Check if unified system is working
echo "🔍 Checking if unified system is working..."
response=$(curl -s http://localhost:8000/health 2>/dev/null || echo "failed")

if [[ $response == *"healthy"* ]]; then
    echo "✅ Unified system is working properly!"
    echo ""
    
    echo "📁 Current backup files:"
    ls -la main*backup*.py 2>/dev/null || echo "No backup files found"
    echo ""
    
    read -p "🗑️  Do you want to remove backup files? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing backup files..."
        rm -f main_backup.py main_postgresql_backup.py main_sqlite_backup.py
        echo "✅ Backup files removed!"
        
        echo ""
        echo "📁 Remaining main files:"
        ls -la main*.py
    else
        echo "💾 Backup files kept for safety"
    fi
else
    echo "❌ Unified system is not responding properly!"
    echo "💾 Keeping all backup files for safety"
    echo ""
    echo "Please ensure the server is running:"
    echo "  python main.py"
fi

echo ""
echo "✅ Cleanup complete!"
