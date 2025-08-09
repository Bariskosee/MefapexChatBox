"""
🔄 Database Migration System
Handles schema versioning, data migrations, and backup/restore operations
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MigrationInfo:
    """Information about a migration"""
    name: str
    version: str
    description: str
    checksum: str
    applied_at: Optional[datetime] = None
    rollback_sql: Optional[str] = None

class DatabaseMigrator:
    """
    Production-grade database migration system
    Supports forward/backward migrations, rollbacks, and validation
    """
    
    def __init__(self, database_manager):
        self.db = database_manager
        self.migrations_dir = Path(__file__).parent / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)
        
    async def create_migration_table(self):
        """Create migrations tracking table"""
        if hasattr(self.db, 'pool') and self.db.pool:  # PostgreSQL/MySQL
            async with self.db.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        id SERIAL PRIMARY KEY,
                        migration_name VARCHAR(255) UNIQUE NOT NULL,
                        version VARCHAR(50) NOT NULL,
                        description TEXT,
                        checksum VARCHAR(64) NOT NULL,
                        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        rollback_sql TEXT,
                        execution_time_ms INTEGER,
                        applied_by VARCHAR(100) DEFAULT CURRENT_USER
                    )
                """)
        else:  # SQLite fallback
            # Handle SQLite case
            pass
    
    async def get_applied_migrations(self) -> List[MigrationInfo]:
        """Get list of applied migrations"""
        if hasattr(self.db, 'pool') and self.db.pool:
            async with self.db.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT migration_name, version, description, checksum, applied_at, rollback_sql
                    FROM schema_migrations 
                    ORDER BY applied_at ASC
                """)
                
                return [
                    MigrationInfo(
                        name=row['migration_name'],
                        version=row['version'],
                        description=row['description'],
                        checksum=row['checksum'],
                        applied_at=row['applied_at'],
                        rollback_sql=row['rollback_sql']
                    )
                    for row in rows
                ]
        return []
    
    async def get_pending_migrations(self) -> List[Path]:
        """Get list of pending migration files"""
        applied = await self.get_applied_migrations()
        applied_names = {m.name for m in applied}
        
        migration_files = sorted(self.migrations_dir.glob("*.sql"))
        return [f for f in migration_files if f.stem not in applied_names]
    
    async def apply_migration(self, migration_file: Path) -> bool:
        """Apply a single migration with full transaction support"""
        migration_content = migration_file.read_text()
        migration_name = migration_file.stem
        
        # Parse migration metadata
        metadata = self._parse_migration_metadata(migration_content)
        
        # Calculate checksum
        checksum = hashlib.sha256(migration_content.encode()).hexdigest()
        
        start_time = datetime.utcnow()
        
        try:
            if hasattr(self.db, 'pool') and self.db.pool:
                async with self.db.pool.acquire() as conn:
                    async with conn.transaction():
                        # Execute migration SQL
                        await conn.execute(migration_content)
                        
                        # Record migration
                        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                        
                        await conn.execute("""
                            INSERT INTO schema_migrations 
                            (migration_name, version, description, checksum, rollback_sql, execution_time_ms)
                            VALUES ($1, $2, $3, $4, $5, $6)
                        """, 
                        migration_name, 
                        metadata.get('version', '1.0.0'),
                        metadata.get('description', ''),
                        checksum,
                        metadata.get('rollback_sql', ''),
                        execution_time
                        )
                        
                        logger.info(f"✅ Applied migration: {migration_name} in {execution_time}ms")
                        return True
            
        except Exception as e:
            logger.error(f"❌ Failed to apply migration {migration_name}: {e}")
            return False
    
    def _parse_migration_metadata(self, content: str) -> Dict[str, str]:
        """Parse migration metadata from comments"""
        metadata = {}
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('-- @'):
                parts = line[4:].split(':', 1)
                if len(parts) == 2:
                    key, value = parts
                    metadata[key.strip()] = value.strip()
        
        return metadata
    
    async def rollback_migration(self, migration_name: str) -> bool:
        """Rollback a specific migration"""
        applied = await self.get_applied_migrations()
        migration_info = next((m for m in applied if m.name == migration_name), None)
        
        if not migration_info:
            logger.error(f"Migration {migration_name} not found in applied migrations")
            return False
        
        if not migration_info.rollback_sql:
            logger.error(f"No rollback SQL defined for migration {migration_name}")
            return False
        
        try:
            if hasattr(self.db, 'pool') and self.db.pool:
                async with self.db.pool.acquire() as conn:
                    async with conn.transaction():
                        # Execute rollback SQL
                        await conn.execute(migration_info.rollback_sql)
                        
                        # Remove migration record
                        await conn.execute(
                            "DELETE FROM schema_migrations WHERE migration_name = $1",
                            migration_name
                        )
                        
                        logger.info(f"✅ Rolled back migration: {migration_name}")
                        return True
            
        except Exception as e:
            logger.error(f"❌ Failed to rollback migration {migration_name}: {e}")
            return False
    
    async def validate_migrations(self) -> Dict[str, Any]:
        """Validate applied migrations against files"""
        results = {
            "valid": True,
            "issues": [],
            "summary": {}
        }
        
        applied = await self.get_applied_migrations()
        migration_files = {f.stem: f for f in self.migrations_dir.glob("*.sql")}
        
        for migration in applied:
            if migration.name not in migration_files:
                results["issues"].append({
                    "type": "missing_file",
                    "migration": migration.name,
                    "message": f"Migration file {migration.name}.sql not found"
                })
                results["valid"] = False
                continue
            
            # Verify checksum
            file_content = migration_files[migration.name].read_text()
            file_checksum = hashlib.sha256(file_content.encode()).hexdigest()
            
            if file_checksum != migration.checksum:
                results["issues"].append({
                    "type": "checksum_mismatch",
                    "migration": migration.name,
                    "message": f"File checksum doesn't match applied migration"
                })
                results["valid"] = False
        
        results["summary"] = {
            "total_applied": len(applied),
            "total_files": len(migration_files),
            "issues_found": len(results["issues"])
        }
        
        return results
    
    async def run_migrations(self) -> Dict[str, Any]:
        """Run all pending migrations"""
        await self.create_migration_table()
        
        pending = await self.get_pending_migrations()
        results = {
            "applied": [],
            "failed": [],
            "skipped": []
        }
        
        for migration_file in pending:
            success = await self.apply_migration(migration_file)
            if success:
                results["applied"].append(migration_file.stem)
            else:
                results["failed"].append(migration_file.stem)
        
        return results
    
    def create_migration_file(self, name: str, description: str = "", version: str = "1.0.0") -> Path:
        """Create a new migration file template"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{name}.sql"
        filepath = self.migrations_dir / filename
        
        template = f"""-- @version: {version}
-- @description: {description}
-- @rollback_sql: -- Add rollback SQL here
-- Migration: {name}
-- Created: {datetime.utcnow().isoformat()}

-- Forward migration SQL
-- Add your migration SQL here



-- Example rollback (update @rollback_sql above):
-- DROP TABLE IF EXISTS example_table;
"""
        
        filepath.write_text(template)
        logger.info(f"✅ Created migration file: {filepath}")
        return filepath

class BackupManager:
    """
    Production-grade backup and restore system
    """
    
    def __init__(self, database_manager):
        self.db = database_manager
        self.backup_dir = Path("./backups")
        self.backup_dir.mkdir(exist_ok=True)
    
    async def create_full_backup(self, 
                               backup_name: Optional[str] = None,
                               compress: bool = True) -> Dict[str, Any]:
        """Create complete database backup"""
        if not backup_name:
            backup_name = f"mefapex_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = self.backup_dir / f"{backup_name}.sql"
        
        start_time = datetime.utcnow()
        
        try:
            # Use database-specific backup
            success = await self.db.create_backup(str(backup_path))
            
            if success:
                backup_size = backup_path.stat().st_size
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                # Compress if requested
                if compress:
                    compressed_path = await self._compress_backup(backup_path)
                    backup_path.unlink()  # Remove uncompressed
                    backup_path = compressed_path
                    backup_size = backup_path.stat().st_size
                
                # Create backup metadata
                metadata = {
                    "backup_name": backup_name,
                    "backup_path": str(backup_path),
                    "backup_size_bytes": backup_size,
                    "created_at": start_time.isoformat(),
                    "duration_seconds": duration,
                    "database_type": self.db.config.database_type,
                    "compressed": compress
                }
                
                # Save metadata
                metadata_path = backup_path.with_suffix('.json')
                metadata_path.write_text(json.dumps(metadata, indent=2))
                
                return {
                    "success": True,
                    "backup_path": str(backup_path),
                    "metadata": metadata
                }
            else:
                return {"success": False, "error": "Backup failed"}
                
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _compress_backup(self, backup_path: Path) -> Path:
        """Compress backup file"""
        import gzip
        import shutil
        
        compressed_path = backup_path.with_suffix('.sql.gz')
        
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return compressed_path
    
    async def restore_backup(self, backup_path: str) -> Dict[str, Any]:
        """Restore database from backup"""
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            return {"success": False, "error": "Backup file not found"}
        
        # Decompress if needed
        if backup_file.suffix == '.gz':
            decompressed_path = await self._decompress_backup(backup_file)
        else:
            decompressed_path = backup_file
        
        try:
            success = await self.db.restore_backup(str(decompressed_path))
            
            if success:
                return {"success": True, "message": "Database restored successfully"}
            else:
                return {"success": False, "error": "Restore failed"}
                
        except Exception as e:
            logger.error(f"❌ Restore failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            # Clean up decompressed file if it was created
            if decompressed_path != backup_file and decompressed_path.exists():
                decompressed_path.unlink()
    
    async def _decompress_backup(self, compressed_path: Path) -> Path:
        """Decompress backup file"""
        import gzip
        import shutil
        
        decompressed_path = compressed_path.with_suffix('')
        
        with gzip.open(compressed_path, 'rb') as f_in:
            with open(decompressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return decompressed_path
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups"""
        backups = []
        
        for backup_file in self.backup_dir.glob("*.sql*"):
            metadata_file = backup_file.with_suffix('.json')
            
            if metadata_file.exists():
                metadata = json.loads(metadata_file.read_text())
                backups.append(metadata)
            else:
                # Create basic metadata for files without it
                stat = backup_file.stat()
                backups.append({
                    "backup_name": backup_file.stem,
                    "backup_path": str(backup_file),
                    "backup_size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "compressed": backup_file.suffix == '.gz'
                })
        
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)
    
    async def cleanup_old_backups(self, keep_days: int = 30) -> Dict[str, Any]:
        """Clean up old backup files"""
        cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
        deleted_files = []
        total_size_freed = 0
        
        for backup_file in self.backup_dir.glob("*.sql*"):
            stat = backup_file.stat()
            file_date = datetime.fromtimestamp(stat.st_mtime)
            
            if file_date < cutoff_date:
                file_size = stat.st_size
                backup_file.unlink()
                deleted_files.append(str(backup_file))
                total_size_freed += file_size
                
                # Also delete metadata file
                metadata_file = backup_file.with_suffix('.json')
                if metadata_file.exists():
                    metadata_file.unlink()
        
        return {
            "deleted_files": deleted_files,
            "total_size_freed_bytes": total_size_freed,
            "cutoff_date": cutoff_date.isoformat()
        }
