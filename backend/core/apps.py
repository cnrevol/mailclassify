from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        """Initialize app when Django is ready"""
        # Import providers only when Django is ready
        from .base_providers import LLMProvider
        from .llm_factory import LLMFactory
        from .model_providers import BertProvider, FastTextProvider

        # Register providers
        LLMFactory.register_provider('bert', BertProvider)
        LLMFactory.register_provider('fasttext', FastTextProvider)
