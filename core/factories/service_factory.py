"""
🏭 Service Factory Pattern Implementation
========================================
Factory classes for creating service instances with proper dependency injection.
"""

from typing import Type, TypeVar, Dict, Any, Optional
from abc import ABC, abstractmethod

from core.interfaces.database_interface import IDatabaseManager
from core.interfaces.auth_interface import IAuthenticationService  
from core.interfaces.model_interface import IModelManager
from core.interfaces.cache_interface import ICacheService
from core.interfaces.config_interface import IConfigurationService
from core.container.dependency_container import DependencyContainer

T = TypeVar('T')


class IServiceFactory(ABC):
    """
    Abstract factory interface for creating services.
    Single Responsibility: Service creation and configuration.
    """
    
    @abstractmethod
    def create_service(self, service_type: Type[T], **kwargs) -> T:
        """Create service instance of specified type"""
        pass
    
    @abstractmethod
    def register_implementation(self, interface: Type, implementation: Type) -> None:
        """Register implementation for interface"""
        pass


class ServiceFactory(IServiceFactory):
    """
    Concrete factory for creating services with dependency injection.
    
    Features:
    - Automatic dependency resolution
    - Configuration-based service creation
    - Environment-specific implementations
    - Singleton pattern support
    """
    
    def __init__(self, container: DependencyContainer, config_service: IConfigurationService):
        self.container = container
        self.config_service = config_service
        self._implementations: Dict[Type, Type] = {}
        self._instances: Dict[Type, Any] = {}
    
    def create_service(self, service_type: Type[T], **kwargs) -> T:
        """Create service instance with dependency injection"""
        # Check if singleton instance already exists
        if service_type in self._instances:
            return self._instances[service_type]
        
        # Use container to resolve dependencies
        if self.container.is_registered(service_type):
            instance = self.container.resolve(service_type)
            self._instances[service_type] = instance
            return instance
        
        # Fall back to manual creation if not registered
        if service_type in self._implementations:
            implementation = self._implementations[service_type]
            instance = self.container._instantiate_with_injection(implementation)
            self._instances[service_type] = instance
            return instance
        
        raise ValueError(f"No implementation registered for {service_type.__name__}")
    
    def register_implementation(self, interface: Type, implementation: Type) -> None:
        """Register implementation for interface"""
        self._implementations[interface] = implementation
        # Also register in container
        self.container.register_singleton(interface, implementation)


class DatabaseServiceFactory:
    """
    Factory specifically for database services.
    Single Responsibility: Database service creation and configuration.
    """
    
    def __init__(self, config_service: IConfigurationService):
        self.config_service = config_service
    
    def create_database_manager(self) -> IDatabaseManager:
        """Create database manager based on configuration"""
        db_config = self.config_service.get_database_config()
        db_type = db_config.get('type', 'postgresql').lower()
        
        if db_type == 'postgresql':
            from services.implementations.database_service import PostgreSQLDatabaseManager
            return PostgreSQLDatabaseManager(self.config_service)
        elif db_type == 'mock':
            from services.implementations.mock_services import MockDatabaseManager
            return MockDatabaseManager()
        else:
            # Force PostgreSQL for all non-mock environments
            from services.implementations.database_service import PostgreSQLDatabaseManager
            return PostgreSQLDatabaseManager(self.config_service)
    
    def create_user_repository(self, db_manager: IDatabaseManager):
        """Create user repository for the database manager"""
        if hasattr(db_manager, 'user_repository'):
            return db_manager.user_repository
        
        # Create based on database type
        from services.implementations.database_service import UserRepository
        return UserRepository(db_manager)
    
    def create_session_repository(self, db_manager: IDatabaseManager):
        """Create session repository for the database manager"""
        if hasattr(db_manager, 'session_repository'):
            return db_manager.session_repository
        
        # Create based on database type
        from services.implementations.database_service import SessionRepository
        return SessionRepository(db_manager)


class AuthServiceFactory:
    """
    Factory for authentication services.
    Single Responsibility: Authentication service creation and configuration.
    """
    
    def __init__(self, config_service: IConfigurationService):
        self.config_service = config_service
    
    def create_auth_service(self, db_manager: IDatabaseManager) -> IAuthenticationService:
        """Create authentication service with dependencies"""
        from services.implementations.auth_service import AuthenticationService
        
        security_config = self.config_service.get_security_config()
        environment = self.config_service.get_environment()
        
        return AuthenticationService(
            secret_key=security_config['secret_key'],
            environment=environment,
            database_manager=db_manager,
            config_service=self.config_service
        )
    
    def create_password_service(self):
        """Create password service"""
        from services.implementations.auth_service import PasswordService
        return PasswordService(self.config_service)
    
    def create_token_service(self):
        """Create token service"""
        from services.implementations.auth_service import TokenService
        security_config = self.config_service.get_security_config()
        return TokenService(
            secret_key=security_config['secret_key'],
            algorithm=security_config.get('algorithm', 'HS256')
        )


class ModelServiceFactory:
    """
    Factory for AI model services.
    Single Responsibility: AI model service creation and configuration.
    """
    
    def __init__(self, config_service: IConfigurationService):
        self.config_service = config_service
    
    def create_model_manager(self) -> IModelManager:
        """Create model manager based on configuration"""
        ai_config = self.config_service.get_ai_config()
        
        if ai_config.get('use_mock', False) or self.config_service.get_environment() == 'test':
            from services.implementations.mock_services import MockModelManager
            return MockModelManager()
        else:
            from services.implementations.model_service import ModelManager
            return ModelManager(self.config_service)
    
    def create_text_generation_service(self, model_manager: IModelManager):
        """Create text generation service"""
        from services.implementations.model_service import TextGenerationService
        return TextGenerationService(model_manager)
    
    def create_embedding_service(self, model_manager: IModelManager):
        """Create embedding service"""
        from services.implementations.model_service import EmbeddingService
        return EmbeddingService(model_manager)


class CacheServiceFactory:
    """
    Factory for cache services.
    Single Responsibility: Cache service creation and configuration.
    """
    
    def __init__(self, config_service: IConfigurationService):
        self.config_service = config_service
    
    def create_cache_service(self) -> ICacheService:
        """Create cache service based on configuration"""
        cache_config = self.config_service.get_cache_config()
        cache_type = cache_config.get('type', 'redis').lower()
        
        if cache_type == 'redis':
            from services.implementations.cache_service import RedisCacheService
            return RedisCacheService(self.config_service)
        elif cache_type == 'memory':
            from services.implementations.cache_service import MemoryCacheService
            return MemoryCacheService()
        elif cache_type == 'mock':
            from services.implementations.mock_services import MockCacheService
            return MockCacheService()
        else:
            raise ValueError(f"Unsupported cache type: {cache_type}")
    
    def create_session_cache_service(self, cache_service: ICacheService):
        """Create session cache service"""
        from services.implementations.cache_service import SessionCacheService
        return SessionCacheService(cache_service)
    
    def create_response_cache_service(self, cache_service: ICacheService):
        """Create response cache service"""
        from services.implementations.cache_service import ResponseCacheService
        return ResponseCacheService(cache_service)


class ServiceFactoryProvider:
    """
    Provider for accessing different service factories.
    Single Responsibility: Factory management and coordination.
    """
    
    def __init__(self, config_service: IConfigurationService):
        self.config_service = config_service
        self.database_factory = DatabaseServiceFactory(config_service)
        self.auth_factory = AuthServiceFactory(config_service)
        self.model_factory = ModelServiceFactory(config_service)
        self.cache_factory = CacheServiceFactory(config_service)
    
    def get_database_factory(self) -> DatabaseServiceFactory:
        """Get database service factory"""
        return self.database_factory
    
    def get_auth_factory(self) -> AuthServiceFactory:
        """Get authentication service factory"""
        return self.auth_factory
    
    def get_model_factory(self) -> ModelServiceFactory:
        """Get model service factory"""
        return self.model_factory
    
    def get_cache_factory(self) -> CacheServiceFactory:
        """Get cache service factory"""
        return self.cache_factory
    
    def create_all_services(self, container: DependencyContainer) -> Dict[str, Any]:
        """Create all services and register them in container"""
        services = {}
        
        # Create services in dependency order
        services['database_manager'] = self.database_factory.create_database_manager()
        services['auth_service'] = self.auth_factory.create_auth_service(services['database_manager'])
        services['model_manager'] = self.model_factory.create_model_manager()
        services['cache_service'] = self.cache_factory.create_cache_service()
        
        # Register in container
        container.register_instance(IDatabaseManager, services['database_manager'])
        container.register_instance(IAuthenticationService, services['auth_service'])
        container.register_instance(IModelManager, services['model_manager'])
        container.register_instance(ICacheService, services['cache_service'])
        
        return services


# Usage example function
def create_application_services(config_service: IConfigurationService) -> DependencyContainer:
    """
    Create and configure all application services using factories.
    
    This demonstrates the complete dependency injection setup:
    1. Create service factories
    2. Create services with proper dependencies
    3. Register in dependency container
    4. Return configured container
    """
    
    # Create dependency container
    container = DependencyContainer()
    
    # Register configuration service first
    container.register_instance(IConfigurationService, config_service)
    
    # Create factory provider
    factory_provider = ServiceFactoryProvider(config_service)
    
    # Create all services and register them
    services = factory_provider.create_all_services(container)
    
    return container
