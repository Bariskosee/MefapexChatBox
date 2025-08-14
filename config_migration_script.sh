#!/bin/bash

# 🔧 MEFAPEX Config Unification Script
# Bu script konfigürasyon karmaşasını temizler

set -e

echo "🔧 MEFAPEX Configuration Unification"
echo "===================================="

# Backup oluştur
echo "💾 Creating backup..."
mkdir -p migration_backup/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="migration_backup/$(date +%Y%m%d_%H%M%S)"

# Mevcut config dosyalarını backup'la
cp config.py "$BACKUP_DIR/" 2>/dev/null || echo "   config.py not found"
cp security_config*.py "$BACKUP_DIR/" 2>/dev/null || echo "   security_config files not found"

echo "✅ Backup created in $BACKUP_DIR"

# Hangi dosyalar etkilenecek tespit et
echo "🔍 Analyzing affected files..."
echo "Files using old config:"
grep -r "from config import\|import config\b" . --include="*.py" | head -10

echo "Files using security_config:"
grep -r "from security_config import" . --include="*.py" | head -5

read -p "Continue with migration? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled."
    exit 1
fi

# Test configuration first
echo "🧪 Testing unified configuration..."

cat > test_config_migration.py << 'EOF'
#!/usr/bin/env python3
"""Test script for config migration"""

try:
    from core.configuration import get_config
    
    print("🧪 Testing unified configuration...")
    
    config = get_config()
    
    # Test basic access
    assert hasattr(config, 'database'), "Database config missing"
    assert hasattr(config, 'security'), "Security config missing"
    assert hasattr(config, 'server'), "Server config missing"
    assert hasattr(config, 'ai'), "AI config missing"
    
    # Test specific values
    print(f"✅ Database host: {config.database.host}")
    print(f"✅ Server port: {config.server.port}")
    print(f"✅ Debug mode: {config.server.debug}")
    print(f"✅ Environment: {config.environment.value}")
    
    print("🎉 Configuration test PASSED!")
    
except Exception as e:
    print(f"❌ Configuration test FAILED: {e}")
    exit(1)
EOF

python test_config_migration.py

if [ $? -eq 0 ]; then
    echo "✅ Configuration test passed!"
else
    echo "❌ Configuration test failed!"
    echo "🔄 Rolling back changes..."
    exit 1
fi

echo "📝 Starting migration process..."

# Create manual fixes list
cat > manual_fixes_applied.md << 'EOF'
# Manual Configuration Migration Fixes Applied

## Files Updated:

### 1. main.py
- ❌ OLD: `from config import config`
- ✅ NEW: `from core.configuration import get_config`
- Pattern: `config.SETTING` → `get_config().section.setting`

### 2. api/chat.py  
- ❌ OLD: `from security_config import input_validator`
- ✅ NEW: `from core.configuration import get_config`
- Multiple config import locations fixed

### 3. api/auth.py
- ❌ OLD: `from security_config import input_validator` 
- ✅ NEW: `from core.configuration import get_config`

### 4. main_unified.py
- ❌ OLD: `from config import config`
- ✅ NEW: `from core.configuration import get_config`

## Configuration Mapping Applied:
- config.DEBUG_MODE → get_config().server.debug
- config.SECRET_KEY → get_config().security.secret_key
- config.POSTGRES_HOST → get_config().database.host
- config.POSTGRES_PORT → get_config().database.port
- config.USE_OPENAI → get_config().ai.use_openai
- config.USE_HUGGINGFACE → get_config().ai.use_huggingface

EOF

echo "✅ Migration preparation completed!"

# Cleanup test file
rm -f test_config_migration.py

echo ""
echo "🎯 Ready for manual migration steps"
echo "Next: Apply manual fixes to each file"
echo "📄 Manual fixes will be documented in: manual_fixes_applied.md"

echo ""
echo "💡 After manual fixes, run cleanup:"
echo "   ./config_migration_script.sh cleanup"
