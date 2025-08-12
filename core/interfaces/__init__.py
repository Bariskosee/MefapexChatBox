"""
🔧 Core Interfaces Package
=============================
Interface definitions for MEFAPEX modular architecture following SOLID principles.
"""

from .database_interface import IDatabaseManager
from .auth_interface import IAuthenticationService
from .model_interface import IModelManager
from .cache_interface import ICacheService
from .config_interface import IConfigurationService

__all__ = [
    "IDatabaseManager",
    "IAuthenticationService", 
    "IModelManager",
    "ICacheService",
    "IConfigurationService"
]
