#!/usr/bin/env python3
"""
🔄 Mikroservis Mimarisi Migrasyon Scripti
==========================================
Karmaşık ve tutarsız mikroservis implementasyonlarını 
birleşik mimariye taşır

YAPILANLAR:
✅ Eski dosyaları yedekle
✅ Circular dependency'leri temizle
✅ Çelişkili implementasyonları kaldır
✅ Unified mimariye geçiş
✅ Yapılandırma güncellemeleri
"""

import os
import shutil
import logging
import asyncio
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MicroserviceMigration:
    """Mikroservis migrayon yöneticisi"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "migration_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.migration_log = []
    
    def log_migration(self, action: str, details: str = ""):
        """Migration işlemini logla"""
        entry = f"[{datetime.now().isoformat()}] {action}"
        if details:
            entry += f" - {details}"
        
        self.migration_log.append(entry)
        logger.info(action + (f": {details}" if details else ""))
    
    def create_backup_directory(self):
        """Backup klasörü oluştur"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.log_migration("Backup klasörü oluşturuldu", str(self.backup_dir))
    
    def backup_file(self, file_path: Path, reason: str = ""):
        """Dosyayı yedekle"""
        if not file_path.exists():
            return
        
        try:
            relative_path = file_path.relative_to(self.project_root)
            backup_path = self.backup_dir / relative_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(file_path, backup_path)
            self.log_migration(f"Dosya yedeklendi: {relative_path}", reason)
            
        except Exception as e:
            self.log_migration(f"Yedekleme hatası: {file_path}", str(e))
    
    def remove_conflicting_files(self):
        """Çelişkili mikroservis dosyalarını kaldır"""
        conflicting_files = [
            "improved_microservice_integration.py",
            "microservice_architecture_fix.py",  # Zaten yok ama referans varsa
        ]
        
        for file_name in conflicting_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                self.backup_file(file_path, "Çelişkili implementasyon")
                file_path.unlink()
                self.log_migration(f"Çelişkili dosya kaldırıldı: {file_name}")
    
    def update_import_statements(self):
        """Import statement'larını güncelle"""
        files_to_update = [
            self.project_root / "main.py"
        ]
        
        # API dosyalarını kontrol et
        api_dir = self.project_root / "api"
        if api_dir.exists():
            files_to_update.extend(api_dir.glob("*.py"))
        
        # Core dosyalarını kontrol et
        core_dir = self.project_root / "core"
        if core_dir.exists():
            files_to_update.extend(core_dir.glob("**/*.py"))
        
        for file_path in files_to_update:
            if file_path.exists() and file_path.is_file():
                self.update_file_imports(file_path)
    
    def update_file_imports(self, file_path: Path):
        """Dosyadaki import'ları güncelle"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Eski import'ları bul ve değiştir
            old_imports = [
                "from improved_microservice_integration import",
                "import improved_microservice_integration",
                "from microservice_architecture_fix import",
                "import microservice_architecture_fix",
                "from services.ai_service.integration import",
                "import services.ai_service.integration"
            ]
            
            replacement_import = "from unified_microservice_architecture import"
            
            for old_import in old_imports:
                if old_import in content:
                    # Satırı bulup yoruma çevir ve yeni import ekle
                    lines = content.split('\n')
                    updated_lines = []
                    
                    for line in lines:
                        if old_import in line and not line.strip().startswith('#'):
                            # Eski import'u yoruma çevir
                            updated_lines.append(f"# MIGRATED: {line}")
                            
                            # İlk import'ta yeni import ekle
                            if replacement_import not in content:
                                updated_lines.append(f"{replacement_import} get_unified_manager, initialize_unified_architecture, cleanup_unified_architecture")
                        else:
                            updated_lines.append(line)
                    
                    content = '\n'.join(updated_lines)
            
            # Function call'ları güncelle
            function_replacements = {
                "get_integration_manager()": "get_unified_manager()",
                "get_model_manager()": "get_unified_manager()",
                "initialize_on_startup()": "initialize_unified_architecture()",
                "cleanup_microservice_integration()": "cleanup_unified_architecture()",
                "diagnose_microservice_issues()": "diagnose_microservice_architecture()",
                "setup_microservice_integration()": "initialize_unified_architecture()"
            }
            
            for old_func, new_func in function_replacements.items():
                content = content.replace(old_func, new_func)
            
            # Değişiklik varsa dosyayı güncelle
            if content != original_content:
                self.backup_file(file_path, "Import güncelleme öncesi")
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.log_migration(f"Import'lar güncellendi: {file_path.name}")
        
        except Exception as e:
            self.log_migration(f"Import güncelleme hatası: {file_path}", str(e))
    
    def clean_ai_service_integration(self):
        """AI servis entegrasyon dosyalarını temizle"""
        ai_service_dir = self.project_root / "services" / "ai_service"
        
        if ai_service_dir.exists():
            # Integration.py dosyasını yedekle ve kaldır
            integration_file = ai_service_dir / "integration.py"
            if integration_file.exists():
                self.backup_file(integration_file, "Eski AI servis entegrasyonu")
                integration_file.unlink()
                self.log_migration("AI servis integration.py kaldırıldı")
            
            # Adapter.py'yi güncelle (unified mimariye uygun hale getir)
            adapter_file = ai_service_dir / "adapter.py"
            if adapter_file.exists():
                self.backup_file(adapter_file, "Adapter güncelleme öncesi")
                self.update_adapter_file(adapter_file)
    
    def update_adapter_file(self, adapter_file: Path):
        """Adapter dosyasını unified mimariye uygun hale getir"""
        try:
            with open(adapter_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Adapter'ı unified mimariyle uyumlu hale getir
            header_comment = '''"""
🔄 AI Mikroservis Adaptörü (Unified Architecture Compatible)
===========================================================
Unified Microservice Architecture ile uyumlu AI servis adaptörü
Bu dosya geriye uyumluluk için korunmuştur.

NOT: Yeni projeler için unified_microservice_architecture.py kullanın
"""

# DEPRECATED: Bu adaptör unified architecture ile değiştirilmiştir
# Geriye uyumluluk için korunmuştur
import warnings
warnings.warn(
    "AI Service Adapter deprecated. Use unified_microservice_architecture instead.",
    DeprecationWarning,
    stacklevel=2
)

'''
            
            updated_content = header_comment + content
            
            with open(adapter_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            self.log_migration("AI servis adapter güncelleştirildi")
            
        except Exception as e:
            self.log_migration(f"Adapter güncelleme hatası: {adapter_file}", str(e))
    
    def create_environment_template(self):
        """Environment template dosyası oluştur"""
        env_template_path = self.project_root / ".env.unified_microservice"
        
        env_template_content = """# Unified Microservice Architecture Configuration
# ================================================

# AI Service Configuration
AI_SERVICE_ENABLED=true
AI_SERVICE_HOST=127.0.0.1
AI_SERVICE_PORT=8001

# Fallback Strategy (progressive, immediate, disabled)
FALLBACK_STRATEGY=progressive

# Health Monitoring
HEALTH_CHECK_INTERVAL=60

# Circuit Breaker Configuration
CIRCUIT_BREAKER_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=30

# Performance Tuning
MAX_RETRY_ATTEMPTS=3
RETRY_DELAY=1.0

# Debug Mode
DEBUG=true
ENVIRONMENT=development
"""
        
        try:
            with open(env_template_path, 'w', encoding='utf-8') as f:
                f.write(env_template_content)
            
            self.log_migration("Environment template oluşturuldu: .env.unified_microservice")
            
        except Exception as e:
            self.log_migration("Environment template oluşturma hatası", str(e))
    
    def update_docker_compose(self):
        """Docker compose dosyasını güncelle"""
        docker_compose_path = self.project_root / "docker-compose.yml"
        
        if not docker_compose_path.exists():
            return
        
        try:
            with open(docker_compose_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Environment variable'ları ekle
            env_additions = """
      # Unified Microservice Architecture
      - AI_SERVICE_ENABLED=true
      - FALLBACK_STRATEGY=progressive
      - HEALTH_CHECK_INTERVAL=60
      - CIRCUIT_BREAKER_THRESHOLD=5"""
            
            if "AI_SERVICE_ENABLED" not in content:
                # Environment section'ı bul ve ekle
                if "environment:" in content:
                    content = content.replace("environment:", f"environment:{env_additions}")
                    
                    self.backup_file(docker_compose_path, "Unified mimari öncesi")
                    
                    with open(docker_compose_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.log_migration("Docker compose güncelleştirildi")
            
        except Exception as e:
            self.log_migration("Docker compose güncelleme hatası", str(e))
    
    def create_migration_report(self):
        """Migration raporu oluştur"""
        report_path = self.backup_dir / "migration_report.txt"
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("MIKROSERVIS MIMARISI MIGRATION RAPORU\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Migration Tarihi: {datetime.now().isoformat()}\n")
                f.write(f"Proje Root: {self.project_root}\n")
                f.write(f"Backup Klasörü: {self.backup_dir}\n\n")
                
                f.write("YAPILANLAR:\n")
                f.write("-" * 20 + "\n")
                for entry in self.migration_log:
                    f.write(f"{entry}\n")
                
                f.write(f"\n\nTOPLAM İŞLEM: {len(self.migration_log)}\n")
                
                f.write("\n\nSONRAKI ADIMLAR:\n")
                f.write("-" * 20 + "\n")
                f.write("1. Uygulamayı test edin: python main.py\n")
                f.write("2. AI servisini başlatın: python services/ai_service/main.py\n")
                f.write("3. Health check yapın: curl http://localhost:8000/health\n")
                f.write("4. Unified mimari test edin: curl http://localhost:8000/system/microservice-status\n")
                f.write("5. Backup dosyalarını kontrol edin ve gerekirse silin\n")
            
            self.log_migration("Migration raporu oluşturuldu")
            
        except Exception as e:
            self.log_migration("Rapor oluşturma hatası", str(e))
    
    async def run_migration(self):
        """Tam migration işlemini çalıştır"""
        logger.info("🔄 Mikroservis mimarisi migration başlıyor...")
        
        try:
            # 1. Backup klasörü oluştur
            self.create_backup_directory()
            
            # 2. Çelişkili dosyaları kaldır
            self.remove_conflicting_files()
            
            # 3. Import statement'larını güncelle
            self.update_import_statements()
            
            # 4. AI servis entegrasyonunu temizle
            self.clean_ai_service_integration()
            
            # 5. Environment template oluştur
            self.create_environment_template()
            
            # 6. Docker compose güncelle
            self.update_docker_compose()
            
            # 7. Migration raporu oluştur
            self.create_migration_report()
            
            logger.info("✅ Migration başarıyla tamamlandı!")
            logger.info(f"📁 Backup dosyaları: {self.backup_dir}")
            logger.info("🚀 Sonraki adım: python main.py ile uygulamayı test edin")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration hatası: {e}")
            return False

def main():
    """Ana migration fonksiyonu"""
    import sys
    
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.getcwd()
    
    print("🔄 MIKROSERVIS MIMARISI MIGRATION SCRIPTI")
    print("=" * 50)
    print(f"Proje Dizini: {project_root}")
    print()
    
    confirm = input("Migration işlemini başlatmak istiyor musunuz? (y/N): ")
    if confirm.lower() != 'y':
        print("Migration iptal edildi.")
        return
    
    migration = MicroserviceMigration(project_root)
    
    # Async migration çalıştır
    success = asyncio.run(migration.run_migration())
    
    if success:
        print("\n✅ Migration başarıyla tamamlandı!")
        print(f"📁 Backup dosyaları: {migration.backup_dir}")
        print("\n🚀 Sonraki Adımlar:")
        print("1. python main.py - Uygulamayı başlat")
        print("2. python services/ai_service/main.py - AI servisini başlat") 
        print("3. curl http://localhost:8000/health - Health check")
        print("4. curl http://localhost:8000/system/microservice-status - Unified mimari test")
    else:
        print("\n❌ Migration sırasında hatalar oluştu!")
        print(f"📁 Log ve backup dosyalarını kontrol edin: {migration.backup_dir}")

if __name__ == "__main__":
    main()
