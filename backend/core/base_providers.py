from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """LLM提供者基类"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = None

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the model"""
        pass

    @abstractmethod
    def chat(self, messages: list, **kwargs) -> Optional[str]:
        """Chat with the model"""
        pass 