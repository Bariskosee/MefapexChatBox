"""
🏭 Dependency Injection Container
=================================
IoC Container for managing dependencies and implementing Dependency Injection pattern.
"""

from typing import Dict, Any, Callable, TypeVar, Type, Optional
import inspect
import threading
from functools import wraps

T = TypeVar('T')


class ServiceLifetime:
    """Service lifetime definitions"""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class ServiceDescriptor:
    """Service descriptor containing registration information"""
    
    def __init__(
        self,
        interface: Type,
        implementation: Type = None,
        factory: Callable = None,
        instance: Any = None,
        lifetime: str = ServiceLifetime.SINGLETON
    ):
        self.interface = interface
        self.implementation = implementation
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime
        
        if not any([implementation, factory, instance]):
            raise ValueError("Either implementation, factory, or instance must be provided")


class DependencyContainer:
    """
    Dependency Injection Container implementing IoC pattern.
    
    Features:
    - Service registration with different lifetimes
    - Automatic dependency resolution
    - Circular dependency detection
    - Thread-safe singleton creation
    - Constructor injection
    """
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._instances: Dict[Type, Any] = {}
        self._locks: Dict[Type, threading.Lock] = {}
        self._resolving: set = set()  # Circular dependency detection
        self._lock = threading.Lock()
    
    def register_singleton(self, interface: Type[T], implementation: Type[T] = None, factory: Callable[[], T] = None) -> 'DependencyContainer':
        """Register a service as singleton"""
        return self._register(interface, implementation, factory, ServiceLifetime.SINGLETON)
    
    def register_transient(self, interface: Type[T], implementation: Type[T] = None, factory: Callable[[], T] = None) -> 'DependencyContainer':
        """Register a service as transient (new instance every time)"""
        return self._register(interface, implementation, factory, ServiceLifetime.TRANSIENT)
    
    def register_instance(self, interface: Type[T], instance: T) -> 'DependencyContainer':
        """Register a pre-created instance"""
        descriptor = ServiceDescriptor(
            interface=interface,
            instance=instance,
            lifetime=ServiceLifetime.SINGLETON
        )
        
        with self._lock:
            self._services[interface] = descriptor
            self._instances[interface] = instance
            
        return self
    
    def _register(self, interface: Type[T], implementation: Type[T] = None, factory: Callable[[], T] = None, lifetime: str = ServiceLifetime.SINGLETON) -> 'DependencyContainer':
        """Internal registration method"""
        if implementation is None and factory is None:
            implementation = interface
        
        descriptor = ServiceDescriptor(
            interface=interface,
            implementation=implementation,
            factory=factory,
            lifetime=lifetime
        )
        
        with self._lock:
            self._services[interface] = descriptor
            if interface not in self._locks:
                self._locks[interface] = threading.Lock()
        
        return self
    
    def resolve(self, interface: Type[T]) -> T:
        """Resolve a service instance"""
        if interface not in self._services:
            raise ValueError(f"Service {interface.__name__} is not registered")
        
        # Circular dependency detection
        if interface in self._resolving:
            raise ValueError(f"Circular dependency detected for {interface.__name__}")
        
        descriptor = self._services[interface]
        
        # Return existing instance for singleton
        if descriptor.lifetime == ServiceLifetime.SINGLETON and interface in self._instances:
            return self._instances[interface]
        
        # Create new instance
        self._resolving.add(interface)
        try:
            instance = self._create_instance(descriptor)
            
            # Store singleton instances
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                with self._locks[interface]:
                    if interface not in self._instances:  # Double-check locking
                        self._instances[interface] = instance
                    return self._instances[interface]
            
            return instance
            
        finally:
            self._resolving.discard(interface)
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create service instance based on descriptor"""
        if descriptor.instance is not None:
            return descriptor.instance
        
        if descriptor.factory is not None:
            return self._call_with_injection(descriptor.factory)
        
        if descriptor.implementation is not None:
            return self._instantiate_with_injection(descriptor.implementation)
        
        raise ValueError("Invalid service descriptor")
    
    def _instantiate_with_injection(self, cls: Type) -> Any:
        """Instantiate class with dependency injection"""
        constructor = cls.__init__
        signature = inspect.signature(constructor)
        
        kwargs = {}
        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue
            
            param_type = param.annotation
            if param_type != inspect.Parameter.empty and param_type in self._services:
                kwargs[param_name] = self.resolve(param_type)
            elif param.default != inspect.Parameter.empty:
                # Use default value if available
                continue
            else:
                # Try to resolve by parameter name if type hint is missing
                if hasattr(param_type, '__origin__'):  # Handle generic types
                    continue
                raise ValueError(f"Cannot resolve parameter '{param_name}' of type '{param_type}' for {cls.__name__}")
        
        return cls(**kwargs)
    
    def _call_with_injection(self, func: Callable) -> Any:
        """Call function with dependency injection"""
        signature = inspect.signature(func)
        
        kwargs = {}
        for param_name, param in signature.parameters.items():
            param_type = param.annotation
            if param_type != inspect.Parameter.empty and param_type in self._services:
                kwargs[param_name] = self.resolve(param_type)
            elif param.default != inspect.Parameter.empty:
                continue
            else:
                raise ValueError(f"Cannot resolve parameter '{param_name}' of type '{param_type}' for {func.__name__}")
        
        return func(**kwargs)
    
    def is_registered(self, interface: Type) -> bool:
        """Check if service is registered"""
        return interface in self._services
    
    def get_registered_services(self) -> Dict[str, str]:
        """Get list of registered services"""
        return {
            service.__name__: descriptor.lifetime 
            for service, descriptor in self._services.items()
        }
    
    def clear(self) -> None:
        """Clear all registrations and instances"""
        with self._lock:
            self._services.clear()
            self._instances.clear()
            self._locks.clear()
            self._resolving.clear()


# Decorator for dependency injection
def inject(container: DependencyContainer):
    """Decorator for automatic dependency injection"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return container._call_with_injection(func)
        return wrapper
    return decorator


# Global container instance
_global_container: Optional[DependencyContainer] = None
_container_lock = threading.Lock()


def get_container() -> DependencyContainer:
    """Get global dependency container"""
    global _global_container
    if _global_container is None:
        with _container_lock:
            if _global_container is None:
                _global_container = DependencyContainer()
    return _global_container


def configure_services(container: DependencyContainer) -> None:
    """Configure service registrations"""
    # This will be implemented in the service configuration module
    pass
