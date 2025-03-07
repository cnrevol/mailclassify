from typing import Dict, Any, Optional, Type
import logging
from django.conf import settings
from .base_providers import LLMProvider
from .models import CCAzureOpenAI, CCOpenAI, CCLLMBase

logger = logging.getLogger('core')

class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI提供者"""
    def initialize(self) -> bool:
        try:
            from openai import AzureOpenAI
            self.model = AzureOpenAI(
                api_key=self.config['api_key'],
                api_version=self.config['api_version'],
                azure_endpoint=self.config['endpoint']
            )
            logger.info("Initialized Azure OpenAI client")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI: {str(e)}")
            return False

    def chat(self, messages: list, **kwargs) -> Optional[str]:
        try:
            response = self.model.chat.completions.create(
                model=self.config['deployment_name'],
                messages=messages,
                temperature=self.config['temperature'],
                max_tokens=self.config['max_tokens']
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Chat error with Azure OpenAI: {str(e)}")
            return None

class OpenAIProvider(LLMProvider):
    """OpenAI提供者"""
    def initialize(self) -> bool:
        try:
            from openai import OpenAI
            self.model = OpenAI(
                api_key=self.config['api_key'],
                organization=self.config.get('organization_id')
            )
            logger.info("Initialized OpenAI client")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {str(e)}")
            return False

    def chat(self, messages: list, **kwargs) -> Optional[str]:
        try:
            response = self.model.chat.completions.create(
                model=self.config['model_id'],
                messages=messages,
                temperature=self.config['temperature'],
                max_tokens=self.config['max_tokens']
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Chat error with OpenAI: {str(e)}")
            return None

class LLMFactory:
    """LLM工厂类"""
    _providers = {}
    _model_classes = {
        'azure': CCAzureOpenAI,
        'openai': CCOpenAI
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[LLMProvider]) -> None:
        """注册LLM提供者"""
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered provider: {name}")

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
            logger.error(f"Unknown provider: {name}")
            return None

        try:
            # Remove name from kwargs if it exists to avoid duplicate argument
            kwargs.pop('name', None)
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
        # 对于BERT和FastText，直接使用默认配置创建实例
        if provider.lower() in ['bert', 'fasttext']:
            return cls.create_instance(provider)

        # 对于其他提供者，从数据库获取配置
        model_class = cls.get_model_class(provider)
        if not model_class:
            logger.error(f"Unknown LLM provider: {provider}")
            return None

        try:
            logger.debug(f"Attempting to fetch {provider} instance with ID: {instance_id}")
            instance = model_class.objects.get(id=instance_id, is_active=True)
            logger.debug(f"Found instance: {instance.name} (ID: {instance.id})")

            # 构建基础配置
            config = {
                'model_id': instance.model_id,
                'endpoint': instance.endpoint,
                'api_key': instance.api_key,
                'api_version': instance.api_version,
                'temperature': instance.temperature,
                'max_tokens': instance.max_tokens,
            }

            # 根据不同提供者添加特定配置
            if isinstance(instance, CCAzureOpenAI):
                config.update({
                    'deployment_name': instance.deployment_name,
                    'resource_name': instance.resource_name,
                })
            elif isinstance(instance, CCOpenAI):
                config.update({
                    'organization_id': instance.organization_id,
                })

            logger.debug(f"Creating {provider} instance with config: {config}")
            return cls.create_instance(name=provider, **config)
        except model_class.DoesNotExist:
            logger.error(f"LLM instance not found: {provider} {instance_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting LLM instance: {str(e)}")
            logger.exception("Detailed error:")
            return None

# Register built-in providers
LLMFactory.register_provider('azure', AzureOpenAIProvider)
LLMFactory.register_provider('openai', OpenAIProvider) 