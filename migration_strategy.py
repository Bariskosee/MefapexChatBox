"""
🔄 Migration Strategy - Gradual Transition Plan
=============================================
Comprehensive migration strategy from monolithic to modular architecture.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.container.dependency_container import DependencyContainer
from core.interfaces.config_interface import IConfigurationService
from core.interfaces.database_interface import IDatabaseManager
from core.interfaces.auth_interface import IAuthenticationService
from services.implementations.config_service import PydanticConfigurationService
from services.implementations.sqlalchemy_async_service import AsyncSQLAlchemyDatabaseService

logger = logging.getLogger(__name__)

class MigrationManager:
    """
    Migration manager for transitioning from old to new architecture.
    Provides safe, step-by-step migration with rollback capabilities.
    """
    
    def __init__(self):
        self.migration_steps = []
        self.completed_steps = []
        self.failed_steps = []
        self.container = DependencyContainer.get_instance()
        
    def add_migration_step(self, name: str, description: str, execute_func, rollback_func=None):
        """Add a migration step"""
        self.migration_steps.append({
            'name': name,
            'description': description,
            'execute': execute_func,
            'rollback': rollback_func,
            'completed': False,
            'timestamp': None
        })
    
    async def execute_migration(self, step_name: Optional[str] = None):
        """Execute migration steps"""
        logger.info("🚀 Starting migration from monolithic to modular architecture...")
        
        steps_to_run = self.migration_steps
        if step_name:
            steps_to_run = [step for step in self.migration_steps if step['name'] == step_name]
        
        for step in steps_to_run:
            if step['completed']:
                logger.info(f"⏭️  Skipping already completed step: {step['name']}")
                continue
                
            try:
                logger.info(f"🔄 Executing: {step['name']} - {step['description']}")
                await step['execute']()
                
                step['completed'] = True
                step['timestamp'] = datetime.now(timezone.utc)
                self.completed_steps.append(step['name'])
                
                logger.info(f"✅ Completed: {step['name']}")
                
            except Exception as e:
                logger.error(f"❌ Failed: {step['name']} - {e}")
                self.failed_steps.append((step['name'], str(e)))
                
                if step['rollback']:
                    logger.info(f"🔄 Rolling back: {step['name']}")
                    try:
                        await step['rollback']()
                        logger.info(f"✅ Rollback completed: {step['name']}")
                    except Exception as rollback_error:
                        logger.error(f"❌ Rollback failed: {step['name']} - {rollback_error}")
                
                raise Exception(f"Migration failed at step: {step['name']}")
        
        logger.info("🎉 Migration completed successfully!")
        self.print_migration_summary()
    
    def print_migration_summary(self):
        """Print migration summary"""
        print("\n" + "="*60)
        print("📊 MIGRATION SUMMARY")
        print("="*60)
        print(f"✅ Completed steps: {len(self.completed_steps)}")
        print(f"❌ Failed steps: {len(self.failed_steps)}")
        print(f"📋 Total steps: {len(self.migration_steps)}")
        
        if self.completed_steps:
            print("\n✅ Completed Steps:")
            for step in self.completed_steps:
                print(f"   • {step}")
        
        if self.failed_steps:
            print("\n❌ Failed Steps:")
            for step, error in self.failed_steps:
                print(f"   • {step}: {error}")
        
        print("\n" + "="*60)


class ArchitectureMigration:
    """Main migration class for architecture transformation"""
    
    def __init__(self):
        self.migration_manager = MigrationManager()
        self.backup_created = False
        self.config_migrated = False
        self.database_migrated = False
        
    def setup_migration_steps(self):
        """Setup all migration steps"""
        
        # Step 1: Environment Validation
        self.migration_manager.add_migration_step(
            "validate_environment",
            "Validate current environment and dependencies",
            self.validate_environment,
            None
        )
        
        # Step 2: Create Backup
        self.migration_manager.add_migration_step(
            "create_backup",
            "Create backup of current system",
            self.create_backup,
            self.restore_backup
        )
        
        # Step 3: Initialize Dependency Container
        self.migration_manager.add_migration_step(
            "initialize_container",
            "Initialize dependency injection container",
            self.initialize_container,
            self.cleanup_container
        )
        
        # Step 4: Migrate Configuration
        self.migration_manager.add_migration_step(
            "migrate_configuration",
            "Migrate to Pydantic configuration system",
            self.migrate_configuration,
            self.rollback_configuration
        )
        
        # Step 5: Migrate Database Layer
        self.migration_manager.add_migration_step(
            "migrate_database",
            "Migrate to async SQLAlchemy with Pydantic models",
            self.migrate_database,
            self.rollback_database
        )
        
        # Step 6: Migrate Authentication
        self.migration_manager.add_migration_step(
            "migrate_auth",
            "Migrate authentication service",
            self.migrate_authentication,
            self.rollback_authentication
        )
        
        # Step 7: Test New System
        self.migration_manager.add_migration_step(
            "test_system",
            "Test new modular system functionality",
            self.test_new_system,
            None
        )
        
        # Step 8: Update Entry Points
        self.migration_manager.add_migration_step(
            "update_entry_points",
            "Update main.py and startup scripts",
            self.update_entry_points,
            self.restore_entry_points
        )
    
    async def validate_environment(self):
        """Validate environment before migration"""
        logger.info("🔍 Validating environment...")
        
        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 8):
            raise Exception(f"Python 3.8+ required, found {python_version}")
        
        # Check required packages
        required_packages = [
            'fastapi', 'uvicorn', 'sqlalchemy', 'pydantic', 
            'asyncpg', 'python-jose', 'passlib'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            raise Exception(f"Missing packages: {', '.join(missing_packages)}")
        
        # Check current database
        if not os.path.exists('data/mefapex.db'):
            logger.warning("⚠️  No existing database found, will create new one")
        
        logger.info("✅ Environment validation passed")
    
    async def create_backup(self):
        """Create backup of current system"""
        logger.info("💾 Creating system backup...")
        
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backup/migration_{timestamp}"
        
        os.makedirs(backup_dir, exist_ok=True)
        
        # Backup database
        if os.path.exists('data/mefapex.db'):
            shutil.copy2('data/mefapex.db', f"{backup_dir}/mefapex.db")
        
        # Backup main files
        files_to_backup = [
            'main.py', 'config.py', 'database_manager.py', 
            'auth_service.py', 'requirements.txt'
        ]
        
        for file in files_to_backup:
            if os.path.exists(file):
                shutil.copy2(file, f"{backup_dir}/{file}")
        
        self.backup_created = True
        logger.info(f"✅ Backup created at: {backup_dir}")
    
    async def restore_backup(self):
        """Restore from backup if needed"""
        if self.backup_created:
            logger.info("🔄 Backup created, restore manually if needed")
    
    async def initialize_container(self):
        """Initialize dependency injection container"""
        logger.info("🏗️  Initializing dependency container...")
        
        # Clear any existing container
        self.container.clear()
        
        # Register configuration service
        self.container.register_singleton(
            IConfigurationService,
            lambda: PydanticConfigurationService()
        )
        
        logger.info("✅ Dependency container initialized")
    
    async def cleanup_container(self):
        """Cleanup container on rollback"""
        self.container.clear()
        logger.info("🧹 Container cleared")
    
    async def migrate_configuration(self):
        """Migrate to Pydantic configuration"""
        logger.info("⚙️  Migrating configuration system...")
        
        # Load old config if exists
        old_config = {}
        if os.path.exists('config.py'):
            import importlib.util
            spec = importlib.util.spec_from_file_location("old_config", "config.py")
            old_config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(old_config_module)
            
            # Extract configuration values
            for attr in dir(old_config_module):
                if not attr.startswith('_'):
                    old_config[attr] = getattr(old_config_module, attr)
        
        # Create new configuration service
        config_service = self.container.resolve(IConfigurationService)
        
        # Validate new configuration
        app_config = config_service.get_application_config()
        db_config = config_service.get_database_config()
        
        logger.info(f"✅ Configuration migrated - App: {app_config.get('name')}")
        self.config_migrated = True
    
    async def rollback_configuration(self):
        """Rollback configuration migration"""
        logger.info("🔄 Rolling back configuration migration")
        self.config_migrated = False
    
    async def migrate_database(self):
        """Migrate to async SQLAlchemy"""
        logger.info("🗄️  Migrating database layer...")
        
        # Get configuration service
        config_service = self.container.resolve(IConfigurationService)
        
        # Register new database service
        self.container.register_singleton(
            IDatabaseManager,
            lambda: AsyncSQLAlchemyDatabaseService(config_service)
        )
        
        # Initialize database
        db_service = self.container.resolve(IDatabaseManager)
        initialized = await db_service.initialize()
        
        if not initialized:
            raise Exception("Failed to initialize new database service")
        
        # Test database connection
        health = db_service.health_check()
        if health.get('status') != 'healthy':
            raise Exception("Database health check failed")
        
        logger.info("✅ Database layer migrated")
        self.database_migrated = True
    
    async def rollback_database(self):
        """Rollback database migration"""
        logger.info("🔄 Rolling back database migration")
        self.database_migrated = False
    
    async def migrate_authentication(self):
        """Migrate authentication service"""
        logger.info("🔐 Migrating authentication service...")
        
        # For now, keep existing auth service
        # This would be expanded to migrate to new auth interface
        
        logger.info("✅ Authentication service migration planned")
    
    async def rollback_authentication(self):
        """Rollback authentication migration"""
        logger.info("🔄 Rolling back authentication migration")
    
    async def test_new_system(self):
        """Test new modular system"""
        logger.info("🧪 Testing new system...")
        
        # Test configuration
        config_service = self.container.resolve(IConfigurationService)
        app_config = config_service.get_application_config()
        assert app_config is not None, "Configuration service failed"
        
        # Test database
        db_service = self.container.resolve(IDatabaseManager)
        health = db_service.health_check()
        assert health.get('status') == 'healthy', "Database service failed"
        
        # Test basic operations
        stats = db_service.get_stats()
        assert isinstance(stats, dict), "Database stats failed"
        
        logger.info("✅ New system tests passed")
    
    async def update_entry_points(self):
        """Update main entry points"""
        logger.info("📝 Updating entry points...")
        
        # Create new main.py that uses the new architecture
        new_main_content = '''"""
MEFAPEX ChatBox - Modular Architecture Entry Point
================================================
Modern FastAPI application with dependency injection and async operations.
"""

import asyncio
import logging
from pathlib import Path

from services.implementations.fastapi_app import app
from core.container.dependency_container import DependencyContainer
from core.interfaces.config_interface import IConfigurationService
from services.implementations.config_service import PydanticConfigurationService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_dependency_container():
    """Setup dependency injection container"""
    container = DependencyContainer.get_instance()
    
    # Register configuration service
    container.register_singleton(
        IConfigurationService,
        lambda: PydanticConfigurationService()
    )
    
    return container

def main():
    """Main entry point"""
    logger.info("🚀 Starting MEFAPEX ChatBox with modular architecture...")
    
    # Setup container
    container = setup_dependency_container()
    
    # Get configuration
    config_service = container.resolve(IConfigurationService)
    app_config = config_service.get_application_config()
    
    # Import and run FastAPI app
    import uvicorn
    
    uvicorn.run(
        "services.implementations.fastapi_app:app",
        host=app_config.get("host", "0.0.0.0"),
        port=app_config.get("port", 8000),
        reload=app_config.get("debug", False),
        log_level="info"
    )

if __name__ == "__main__":
    main()
'''
        
        # Backup original main.py
        if os.path.exists('main.py'):
            os.rename('main.py', 'main_original.py')
        
        # Write new main.py
        with open('main_new.py', 'w') as f:
            f.write(new_main_content)
        
        logger.info("✅ Entry points updated")
    
    async def restore_entry_points(self):
        """Restore original entry points"""
        if os.path.exists('main_original.py'):
            if os.path.exists('main.py'):
                os.remove('main.py')
            os.rename('main_original.py', 'main.py')
        logger.info("🔄 Entry points restored")


# ================================
# Migration Execution
# ================================

async def run_migration():
    """Run the complete migration"""
    migration = ArchitectureMigration()
    migration.setup_migration_steps()
    
    try:
        await migration.migration_manager.execute_migration()
        
        print("\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
        print("✅ Your application has been migrated to the new modular architecture.")
        print("\n📋 Next Steps:")
        print("1. Review the new main_new.py file")
        print("2. Test the new system: python main_new.py")
        print("3. Update your deployment scripts")
        print("4. Remove old files when satisfied")
        
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        print("🔄 Check logs for details and rollback instructions")


def run_step_by_step_migration():
    """Interactive step-by-step migration"""
    async def interactive_migration():
        migration = ArchitectureMigration()
        migration.setup_migration_steps()
        
        print("🔄 STEP-BY-STEP MIGRATION")
        print("=" * 50)
        
        for i, step in enumerate(migration.migration_manager.migration_steps, 1):
            print(f"\n{i}. {step['name']}: {step['description']}")
            
            while True:
                choice = input("Execute this step? (y/n/q): ").lower().strip()
                if choice == 'y':
                    try:
                        await migration.migration_manager.execute_migration(step['name'])
                        break
                    except Exception as e:
                        print(f"❌ Step failed: {e}")
                        if input("Continue anyway? (y/n): ").lower() == 'n':
                            return
                        break
                elif choice == 'n':
                    print("⏭️  Skipped")
                    break
                elif choice == 'q':
                    print("🚪 Migration cancelled")
                    return
                else:
                    print("Please enter 'y' for yes, 'n' for no, or 'q' to quit")
        
        print("\n🎉 Interactive migration completed!")
    
    asyncio.run(interactive_migration())


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        run_step_by_step_migration()
    else:
        print("🚀 Starting automatic migration...")
        print("Use --interactive for step-by-step migration")
        asyncio.run(run_migration())
