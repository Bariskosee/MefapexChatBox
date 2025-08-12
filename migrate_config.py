#!/usr/bin/env python3
"""
🔄 Configuration Migration Script
===============================
Migrates the codebase from scattered config usage to unified configuration system
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class ConfigMigrator:
    """
    Migrate codebase to use unified configuration system
    """
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.migration_log = []
        
        # Patterns to find and replace
        self.patterns = {
            # Direct os.getenv usage
            r'os\.getenv\("([^"]+)",\s*([^)]+)\)': self._migrate_os_getenv,
            r'os\.getenv\("([^"]+)"\)': self._migrate_os_getenv_simple,
            
            # load_dotenv usage
            r'from core.configuration import get_config': 'from core.configuration import get_config',
            r'load_dotenv\(\)': '# Moved to unified configuration system',
            
            # Legacy config imports
            r'from core.configuration import get_config': 'from core.configuration import get_config',
            r'config\.([A-Z_]+)': self._migrate_config_attribute,
        }
        
        # Environment variable mapping to unified config paths
        self.env_mapping = {
            'ENVIRONMENT': 'environment.value',
            'DEBUG': 'server.debug',
            'SECRET_KEY': 'security.secret_key',
            'USE_OPENAI': 'ai.use_openai',
            'USE_HUGGINGFACE': 'ai.use_huggingface',
            'OPENAI_API_KEY': 'ai.openai_api_key',
            'POSTGRES_HOST': 'database.host',
            'POSTGRES_PORT': 'database.port',
            'POSTGRES_USER': 'database.user',
            'POSTGRES_PASSWORD': 'database.password',
            'POSTGRES_DB': 'database.database',
            'DATABASE_URL': 'database.url',
            'QDRANT_HOST': 'qdrant.host',
            'QDRANT_PORT': 'qdrant.port',
            'RATE_LIMIT_REQUESTS': 'rate_limit.requests_per_minute',
            'RATE_LIMIT_CHAT': 'rate_limit.chat_requests_per_minute',
            'ACCESS_TOKEN_EXPIRE_MINUTES': 'security.access_token_expire_minutes',
            'MIN_PASSWORD_LENGTH': 'security.min_password_length',
            'MAX_PASSWORD_LENGTH': 'security.max_password_length',
            'DEMO_USER_ENABLED': 'security.demo_user_enabled',
            'DEMO_PASSWORD': 'security.demo_password',
            'MAX_LOGIN_ATTEMPTS': 'security.max_login_attempts',
            'BLOCK_DURATION_MINUTES': 'security.block_duration_minutes',
            'PORT': 'server.port',
            'ALLOWED_ORIGINS': 'server.allowed_origins',
            'ALLOWED_HOSTS': 'server.allowed_hosts',
            'MAX_MESSAGE_LENGTH': 'validation.max_message_length',
            'MIN_MESSAGE_LENGTH': 'validation.min_message_length',
            'MAX_USERNAME_LENGTH': 'validation.max_username_length',
            'MIN_USERNAME_LENGTH': 'validation.min_username_length',
            'SENTENCE_MODEL': 'ai.sentence_model',
            'HUGGINGFACE_MODEL': 'ai.huggingface_model'
        }
    
    def _migrate_os_getenv(self, match) -> str:
        """Migrate os.getenv pattern to unified config"""
        env_var = match.group(1)
        default_value = match.group(2) if len(match.groups()) > 1 else None
        
        if env_var in self.env_mapping:
            config_path = self.env_mapping[env_var]
            if default_value:
                return f'get_config().{config_path}'
            else:
                return f'get_config().{config_path}'
        else:
            # Unknown env var, keep as is but log
            self.migration_log.append(f"⚠️ Unknown environment variable: {env_var}")
            return match.group(0)
    
    def _migrate_os_getenv_simple(self, match) -> str:
        """Migrate simple os.getenv pattern"""
        env_var = match.group(1)
        if env_var in self.env_mapping:
            config_path = self.env_mapping[env_var]
            return f'get_config().{config_path}'
        else:
            self.migration_log.append(f"⚠️ Unknown environment variable: {env_var}")
            return match.group(0)
    
    def _migrate_config_attribute(self, match) -> str:
        """Migrate config.ATTRIBUTE patterns"""
        attr = match.group(1)
        if attr in self.env_mapping:
            config_path = self.env_mapping[attr]
            return f'get_config().{config_path}'
        else:
            self.migration_log.append(f"⚠️ Unknown config attribute: {attr}")
            return match.group(0)
    
    def scan_files(self) -> List[Path]:
        """Scan for Python files that need migration"""
        python_files = []
        
        for file_path in self.project_root.rglob("*.py"):
            # Skip virtual environment, cache, and migration files
            if any(part in file_path.parts for part in ['.venv', '__pycache__', '.git', 'migration']):
                continue
            
            # Skip the unified configuration files themselves
            if 'core/configuration' in str(file_path) or 'core/services/config' in str(file_path):
                continue
            
            python_files.append(file_path)
        
        return python_files
    
    def analyze_file(self, file_path: Path) -> Dict[str, List[str]]:
        """Analyze a file for configuration patterns"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return {}
        
        findings = {
            'os_getenv': [],
            'load_dotenv': [],
            'config_imports': [],
            'config_usage': []
        }
        
        # Find os.getenv patterns
        for match in re.finditer(r'os\.getenv\([^)]+\)', content):
            findings['os_getenv'].append(match.group(0))
        
        # Find load_dotenv patterns
        if 'load_dotenv' in content:
            findings['load_dotenv'].append('load_dotenv usage found')
        
        # Find config imports
        if 'from config import' in content or 'import config' in content:
            findings['config_imports'].append('config import found')
        
        # Find config.ATTRIBUTE usage
        for match in re.finditer(r'config\.[A-Z_]+', content):
            findings['config_usage'].append(match.group(0))
        
        return findings
    
    def migrate_file(self, file_path: Path, dry_run: bool = True) -> bool:
        """Migrate a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return False
        
        content = original_content
        changes_made = False
        
        # Apply simple string replacements first
        for pattern, replacement in self.patterns.items():
            if callable(replacement):
                # For complex patterns, use regex with function
                def replace_func(match):
                    return replacement(match)
                
                new_content = re.sub(pattern, replace_func, content)
            else:
                # Simple string replacement
                new_content = re.sub(pattern, replacement, content)
            
            if new_content != content:
                changes_made = True
                content = new_content
        
        # Add necessary import if changes were made
        if changes_made and 'from core.configuration import get_config' not in content:
            # Find a good place to add the import
            lines = content.split('\n')
            import_line = 'from core.configuration import get_config'
            
            # Find the last import line
            last_import_idx = -1
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')) and not line.strip().startswith('#'):
                    last_import_idx = i
            
            if last_import_idx >= 0:
                lines.insert(last_import_idx + 1, import_line)
            else:
                # No imports found, add at the top after docstring/comments
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('"""'):
                        insert_idx = i
                        break
                lines.insert(insert_idx, import_line)
                lines.insert(insert_idx + 1, '')
            
            content = '\n'.join(lines)
        
        if changes_made and not dry_run:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"✅ Migrated: {file_path}")
            except Exception as e:
                logger.error(f"Error writing {file_path}: {e}")
                return False
        elif changes_made:
            logger.info(f"🔍 Would migrate: {file_path}")
        
        return changes_made
    
    def run_migration(self, dry_run: bool = True):
        """Run the complete migration process"""
        logger.info("🔄 Starting Configuration Migration")
        logger.info("=" * 50)
        
        files_to_check = self.scan_files()
        logger.info(f"📁 Found {len(files_to_check)} Python files to analyze")
        
        files_with_issues = {}
        files_migrated = 0
        
        # First pass: analyze all files
        for file_path in files_to_check:
            findings = self.analyze_file(file_path)
            
            if any(findings.values()):
                files_with_issues[file_path] = findings
        
        logger.info(f"⚠️ Found {len(files_with_issues)} files with configuration issues")
        
        # Second pass: migrate files
        for file_path, findings in files_with_issues.items():
            logger.info(f"\n📄 Processing: {file_path}")
            
            for category, items in findings.items():
                if items:
                    logger.info(f"  {category}: {len(items)} issues")
                    for item in items[:3]:  # Show first 3 items
                        logger.info(f"    - {item}")
                    if len(items) > 3:
                        logger.info(f"    ... and {len(items) - 3} more")
            
            # Migrate the file
            if self.migrate_file(file_path, dry_run):
                files_migrated += 1
        
        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("🎯 Migration Summary")
        logger.info("=" * 50)
        logger.info(f"📊 Files analyzed: {len(files_to_check)}")
        logger.info(f"⚠️ Files with issues: {len(files_with_issues)}")
        logger.info(f"🔄 Files {'would be ' if dry_run else ''}migrated: {files_migrated}")
        
        if self.migration_log:
            logger.info("\n⚠️ Migration Warnings:")
            for warning in set(self.migration_log):
                logger.info(f"  - {warning}")
        
        if dry_run:
            logger.info("\n💡 This was a dry run. Use --apply to actually migrate files.")
        else:
            logger.info("\n✅ Migration completed!")
            logger.info("🔍 Please review the changes and test your application.")
    
    def create_migration_checklist(self):
        """Create a checklist for manual migration steps"""
        checklist = """
# 🔄 Configuration Migration Checklist

## ✅ Automated Migration Completed
- [ ] Run the migration script with `--apply`
- [ ] Review all changed files
- [ ] Test application startup

## 🔧 Manual Steps Required

### 1. Update Imports
Replace scattered imports with unified configuration:
```python
# ❌ Old way
from core.configuration import get_config
from core.configuration import get_config
import os

# ✅ New way  
from core.configuration import get_config
```

### 2. Update Configuration Access
Replace direct environment variable access:
```python
# ❌ Old way
database_host = get_config().database.host
secret_key = get_config().security.secret_key

# ✅ New way
config = get_config()
database_host = config.database.host
secret_key = config.security.secret_key
```

### 3. Service Dependency Injection
For services, use the configuration service:
```python
# ✅ Recommended for services
from core.services.config_service import get_config_service

config_service = get_config_service()
db_config = config_service.get_database_config()
```

### 4. Environment Variable Cleanup
- [ ] Remove duplicate `# Moved to unified configuration system` calls
- [ ] Consolidate environment variables in `.env`
- [ ] Remove hardcoded values

### 5. Testing
- [ ] Test all configuration scenarios
- [ ] Test production environment setup
- [ ] Test Docker configuration
- [ ] Test environment variable override

## 🎯 Benefits Achieved
- ✅ Single source of truth for configuration
- ✅ Type safety and validation
- ✅ Environment-specific configurations
- ✅ Production security validation  
- ✅ Backward compatibility maintained

## 🚨 Common Issues to Check
- [ ] Service initialization order
- [ ] Configuration validation errors
- [ ] Missing environment variables
- [ ] Type conversion issues
"""
        
        checklist_path = self.project_root / "MIGRATION_CHECKLIST.md"
        with open(checklist_path, 'w') as f:
            f.write(checklist)
        
        logger.info(f"📋 Migration checklist created: {checklist_path}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate MEFAPEX configuration system")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--apply", action="store_true", help="Apply changes (not dry run)")
    parser.add_argument("--checklist", action="store_true", help="Create migration checklist")
    
    args = parser.parse_args()
    
    migrator = ConfigMigrator(args.project_root)
    
    if args.checklist:
        migrator.create_migration_checklist()
    
    migrator.run_migration(dry_run=not args.apply)

if __name__ == "__main__":
    main()
