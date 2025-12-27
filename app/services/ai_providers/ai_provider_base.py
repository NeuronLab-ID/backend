"""
AI Provider Base - Abstract interface for AI providers.

Follows SOLID principles:
- Single Responsibility: Each provider handles its own logic
- Open/Closed: Easy to add new providers without modifying existing code
- Liskov Substitution: Providers can be swapped
- Interface Segregation: Clean interface for AI operations
- Dependency Inversion: Depend on abstractions
"""
from abc import ABC, abstractmethod
from typing import Optional


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        pass
    
    @abstractmethod
    async def generate_hint(self, problem: dict, user_code: str, error: str) -> Optional[str]:
        """
        Generate a hint for code error.
        
        Args:
            problem: Problem data (title, description, etc.)
            user_code: User's code that has an error
            error: The error message
        
        Returns:
            Short hint (1-2 sentences) or None on error
        """
        pass
    
    @abstractmethod
    async def generate_reasoning(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """
        Generate step-by-step reasoning.
        
        Args:
            prompt: The reasoning prompt
            system_prompt: Optional system context
        
        Returns:
            Generated reasoning text or None on error
        """
        pass
    
    def is_configured(self) -> bool:
        """Check if provider is properly configured. Override if needed."""
        return True


class SearchProvider(ABC):
    """Abstract base class for search providers (optional capability)."""
    
    @abstractmethod
    async def search(self, topic: str, context: str = "") -> Optional[str]:
        """
        Search for information about a topic.
        
        Args:
            topic: Topic to search for
            context: Additional context
        
        Returns:
            Search results or None on error
        """
        pass
