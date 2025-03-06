from typing import Dict, Any, Optional, Type
from abc import ABC, abstractmethod
import logging
from django.conf import settings
from .models import CCAzureOpenAI, CCOpenAI, CCLLMBase

logger = logging.getLogger('core')

class LLMProvider(ABC):
    """
    LLM提供者基类
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._client = None

    @abstractmethod
    def initialize(self) -> None:
        """初始化LLM客户端"""
        pass

    @abstractmethod
    def get_completion(self, prompt: str) -> str:
        """获取补全结果"""
        pass

    @property
    def client(self):
        if self._client is None:
            self.initialize()
        return self._client

class AzureOpenAIProvider(LLMProvider):
    """
    Azure OpenAI提供者
    """
    def initialize(self) -> None:
        try:
            from openai import AzureOpenAI
            self._client = AzureOpenAI(
                api_key=self.config['api_key'],
                api_version=self.config['api_version'],
                azure_endpoint=self.config['endpoint']
            )
            logger.info(f"Initialized Azure OpenAI client for {self.config['name']}")
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
            raise

    def get_completion(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.config['deployment_name'],
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config['temperature'],
                max_tokens=self.config['max_tokens']
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error getting completion from Azure OpenAI: {str(e)}")
            raise

class OpenAIProvider(LLMProvider):
    """
    OpenAI提供者
    """
    def initialize(self) -> None:
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.config['api_key'],
                organization=self.config.get('organization_id')
            )
            logger.info(f"Initialized OpenAI client for {self.config['name']}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise

    def get_completion(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.config['model_id'],
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config['temperature'],
                max_tokens=self.config['max_tokens']
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error getting completion from OpenAI: {str(e)}")
            raise

class LLMFactory:
    """
    LLM工厂类
    """
    _providers = {
        'azure': AzureOpenAIProvider,
        'openai': OpenAIProvider
    }

    _model_classes = {
        'azure': CCAzureOpenAI,
        'openai': CCOpenAI
    }

    @classmethod
    def get_provider(cls, name: str) -> Optional[Type[LLMProvider]]:
        """获取LLM提供者类"""
        return cls._providers.get(name.lower())

    @classmethod
    def get_model_class(cls, name: str) -> Optional[Type[CCLLMBase]]:
        """获取LLM模型类"""
        return cls._model_classes.get(name.lower())

    @classmethod
    def create_instance(cls, name: str, **kwargs) -> Optional[LLMProvider]:
        """创建LLM实例"""
        provider_class = cls.get_provider(name)
        if not provider_class:
            logger.error(f"Unknown LLM provider: {name}")
            return None

        try:
            provider = provider_class(kwargs)
            provider.initialize()
            logger.info(f"Successfully created {name} instance")
            return provider
        except Exception as e:
            logger.error(f"Failed to create {name} instance: {str(e)}")
            return None

    @classmethod
    def get_instance_by_id(cls, provider: str, instance_id: int) -> Optional[LLMProvider]:
        """通过ID获取LLM实例"""
        model_class = cls.get_model_class(provider)
        if not model_class:
            logger.error(f"Unknown LLM provider: {provider}")
            return None

        try:
            instance = model_class.objects.get(id=instance_id, is_active=True)
            config = {
                'name': instance.name,
                'model_id': instance.model_id,
                'endpoint': instance.endpoint,
                'api_key': instance.api_key,
                'api_version': instance.api_version,
                'temperature': instance.temperature,
                'max_tokens': instance.max_tokens,
            }

            if provider == 'azure':
                config.update({
                    'deployment_name': instance.deployment_name,
                    'resource_name': instance.resource_name,
                })
            elif provider == 'openai':
                config.update({
                    'organization_id': instance.organization_id,
                })

            return cls.create_instance(provider, **config)
        except model_class.DoesNotExist:
            logger.error(f"LLM instance not found: {provider} {instance_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting LLM instance: {str(e)}")
            return None 