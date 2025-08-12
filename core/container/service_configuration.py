"""
🏭 Service Configuration
========================
Central configuration for dependency injection container.
"""

from core.container.dependency_container import DependencyContainer

# Import interfaces
from core.interfaces.database_interface import IDatabaseManager, IUserRepository, ISessionRepository
from core.interfaces.auth_interface import IAuthenticationService, IPasswordService, ITokenService
from core.interfaces.model_interface import IModelManager, ITextGenerationService, IEmbeddingService
from core.interfaces.cache_interface import ICacheService, ISessionCacheService, IResponseCacheService
from core.interfaces.config_interface import IConfigurationService, IDatabaseConfigurationService

# Import implementations
from services.implementations.database_service import PostgreSQLDatabaseManager, UserRepository, SessionRepository
from services.implementations.auth_service import AuthenticationService, PasswordService, TokenService
from services.implementations.model_service import ModelManager, TextGenerationService, EmbeddingService
from services.implementations.cache_service import RedisCacheService, SessionCacheService, ResponseCacheService
from services.implementations.config_service import ConfigurationService, DatabaseConfigurationService


def configure_services(container: DependencyContainer) -> None:
    """
    Configure all service registrations for the application.
    
    This follows the Dependency Inversion Principle:
    - High-level modules depend on abstractions (interfaces)
    - Low-level modules implement those abstractions
    """
    
    # 🔧 Configuration Services
    container.register_singleton(IConfigurationService, ConfigurationService)
    container.register_singleton(IDatabaseConfigurationService, DatabaseConfigurationService)
    
    # 🗄️ Database Services
    container.register_singleton(IDatabaseManager, PostgreSQLDatabaseManager)
    container.register_singleton(IUserRepository, UserRepository)
    container.register_singleton(ISessionRepository, SessionRepository)
    
    # 🔐 Authentication Services  
    container.register_singleton(IAuthenticationService, AuthenticationService)
    container.register_singleton(IPasswordService, PasswordService)
    container.register_singleton(ITokenService, TokenService)
    
    # 🤖 AI Model Services
    container.register_singleton(IModelManager, ModelManager)
    container.register_singleton(ITextGenerationService, TextGenerationService)
    container.register_singleton(IEmbeddingService, EmbeddingService)
    
    # 💾 Cache Services
    container.register_singleton(ICacheService, RedisCacheService)
    container.register_singleton(ISessionCacheService, SessionCacheService)
    container.register_singleton(IResponseCacheService, ResponseCacheService)


def configure_test_services(container: DependencyContainer) -> None:
    """
    Configure services for testing environment with mocks.
    """
    from services.implementations.mock_services import (
        MockDatabaseManager, 
        MockAuthenticationService,
        MockModelManager,
        MockCacheService
    )
    
    # Override with mock implementations for testing
    container.register_singleton(IDatabaseManager, MockDatabaseManager)
    container.register_singleton(IAuthenticationService, MockAuthenticationService)
    container.register_singleton(IModelManager, MockModelManager)
    container.register_singleton(ICacheService, MockCacheService)


# Service factory functions for complex instantiation
def create_database_manager(config_service: IConfigurationService) -> IDatabaseManager:
    """Factory function for database manager with configuration injection"""
    db_config = config_service.get_database_config()
    return PostgreSQLDatabaseManager(**db_config)


def create_auth_service(config_service: IConfigurationService, db_manager: IDatabaseManager) -> IAuthenticationService:
    """Factory function for authentication service with dependencies"""
    auth_config = config_service.get_security_config()
    return AuthenticationService(
        secret_key=auth_config['secret_key'],
        environment=config_service.get_environment(),
        database_manager=db_manager
    )


# Advanced configuration with factories
def configure_services_with_factories(container: DependencyContainer) -> None:
    """Configure services using factory functions for complex dependencies"""
    
    # Register configuration service first
    container.register_singleton(IConfigurationService, ConfigurationService)
    
    # Register other services with factories
    container.register_singleton(
        IDatabaseManager, 
        factory=lambda: create_database_manager(container.resolve(IConfigurationService))
    )
    
    container.register_singleton(
        IAuthenticationService,
        factory=lambda: create_auth_service(
            container.resolve(IConfigurationService),
            container.resolve(IDatabaseManager)
        )
    )
