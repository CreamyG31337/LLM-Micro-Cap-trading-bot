"""Repository pattern implementation for data access."""

from .base_repository import (
    BaseRepository,
    RepositoryError,
    DataValidationError,
    DataNotFoundError,
    DataCorruptionError
)
from .csv_repository import CSVRepository
from .repository_factory import (
    RepositoryFactory,
    RepositoryContainer,
    get_repository_container,
    configure_repositories,
    get_repository,
    set_repository
)
from .integration import (
    initialize_repositories_from_config,
    get_configured_repository
)

__all__ = [
    # Base repository interface
    'BaseRepository',
    'RepositoryError',
    'DataValidationError', 
    'DataNotFoundError',
    'DataCorruptionError',
    
    # Concrete implementations
    'CSVRepository',
    
    # Factory and dependency injection
    'RepositoryFactory',
    'RepositoryContainer',
    'get_repository_container',
    'configure_repositories',
    'get_repository',
    'set_repository',
    
    # Integration functions
    'initialize_repositories_from_config',
    'get_configured_repository',
]