import json
import logging
from typing import Dict, Any, List, Optional
from smolagents import Tool
from django.conf import settings
from django.apps import apps

# Import models through Django's app registry
CCEmail = apps.get_model('core', 'CCEmail')

# Import from core package
from core.llm_factory import LLMFactory
from core.model_providers import BertProvider, FastTextProvider

logger = logging.getLogger(__name__)

class EmailClassificationTool(Tool):
    """Base class for email classification tools"""
    def __init__(self, name: str, description: str):
        super().__init__(name=name, description=description)
        self.available_categories: List[str] = []  # Will be set by the agent
        logger.debug(f"Initialized EmailClassificationTool: {name}")

    def set_categories(self, categories: List[str]) -> None:
        """Set available categories for classification"""
        self.available_categories = categories
        logger.debug(f"Set categories: {categories}")

class LLMClassificationTool(EmailClassificationTool):
    """Tool for classifying emails using LLM"""
    def __init__(self):
        super().__init__(
            name="llm_classify",
            description="Classify emails using LLM model"
        )
        self.llm_provider = None
        logger.info("Initialized LLMClassificationTool")

    def setup(self, provider_name: str = "azure", instance_id: int = 1) -> None:
        """Setup LLM provider"""
        logger.info(f"Setting up LLM provider: {provider_name}, instance: {instance_id}")
        self.llm_provider = LLMFactory.get_instance_by_id(provider_name, instance_id)
        if self.llm_provider:
            logger.info("LLM provider initialized successfully")
        else:
            logger.error("Failed to initialize LLM provider")

    def __call__(self, email) -> Dict[str, Any]:
        """Classify email using LLM"""
        try:
            if not self.llm_provider:
                logger.error("LLM provider not initialized")
                raise ValueError("LLM provider not initialized")

            # Prepare system message
            system_message = {
                "role": "system",
                "content": f"""You are an email classification system. Classify the email into one of these categories:
                {', '.join(self.available_categories)}
                
                Provide your response in JSON format with these fields:
                - classification: the chosen category
                - confidence: a score between 0 and 1
                - explanation: brief reason for the classification"""
            }
            logger.debug("Prepared system message for LLM")

            # Prepare email content
            user_message = {
                "role": "user",
                "content": f"""Subject: {email.subject}
                From: {email.sender}
                Content: {email.content[:1000]}  # Limit content length
                Attachments: {len(email.attachments_info)} files"""
            }
            logger.debug("Prepared user message for LLM")

            # Get classification from LLM
            response = self.llm_provider.chat([system_message, user_message])
            if not response:
                logger.error("No response from LLM")
                raise ValueError("No response from LLM")

            # Parse response
            result = json.loads(response)
            logger.info(f"LLM classification result: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in LLM classification: {str(e)}", exc_info=True)
            return {
                "classification": "unknown",
                "confidence": 0.0,
                "explanation": f"Error: {str(e)}"
            }

class BertClassificationTool(EmailClassificationTool):
    """Tool for classifying emails using BERT"""
    def __init__(self):
        super().__init__(
            name="bert_classify",
            description="Classify emails using BERT model"
        )
        self.model_provider = None

    def setup(self) -> None:
        """Setup BERT provider"""
        self.model_provider = LLMFactory.get_instance_by_id("bert", 0)

    def __call__(self, email) -> Dict[str, Any]:
        """Classify email using BERT"""
        try:
            if not self.model_provider:
                raise ValueError("BERT provider not initialized")

            # Prepare message for classification
            message = {
                "role": "user",
                "content": f"{email.subject}\n{email.content[:1000]}"
            }

            # Get classification from BERT
            response = self.model_provider.chat([message])
            if not response:
                raise ValueError("No response from BERT")

            # Parse response
            result = json.loads(response)
            logger.info(f"BERT classification result: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in BERT classification: {str(e)}")
            return {
                "classification": "unknown",
                "confidence": 0.0,
                "explanation": f"Error: {str(e)}"
            }

class FastTextClassificationTool(EmailClassificationTool):
    """Tool for classifying emails using FastText"""
    def __init__(self):
        super().__init__(
            name="fasttext_classify",
            description="Classify emails using FastText model"
        )
        self.model_provider = None

    def setup(self) -> None:
        """Setup FastText provider"""
        self.model_provider = LLMFactory.get_instance_by_id("fasttext", 0)

    def __call__(self, email) -> Dict[str, Any]:
        """Classify email using FastText"""
        try:
            if not self.model_provider:
                raise ValueError("FastText provider not initialized")

            # Prepare message for classification
            message = {
                "role": "user",
                "content": f"{email.subject}\n{email.content[:1000]}"
            }

            # Get classification from FastText
            response = self.model_provider.chat([message])
            if not response:
                raise ValueError("No response from FastText")

            # Parse response
            result = json.loads(response)
            logger.info(f"FastText classification result: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in FastText classification: {str(e)}")
            return {
                "classification": "unknown",
                "confidence": 0.0,
                "explanation": f"Error: {str(e)}"
            }

class EmailClassificationAgent:
    """Agent for email classification using multiple models"""
    def __init__(self, categories: List[str]):
        # Initialize classification tools
        self.llm_tool = LLMClassificationTool()
        self.bert_tool = BertClassificationTool()
        self.fasttext_tool = FastTextClassificationTool()

        # Set available categories for all tools
        for tool in [self.llm_tool, self.bert_tool, self.fasttext_tool]:
            tool.set_categories(categories)

    def setup(self, llm_provider: str = "azure", llm_instance_id: int = 1) -> None:
        """Setup all classification tools"""
        try:
            # Setup LLM tool
            self.llm_tool.setup(llm_provider, llm_instance_id)
            logger.info("LLM tool initialized successfully")

            # Setup BERT tool
            self.bert_tool.setup()
            logger.info("BERT tool initialized successfully")

            # Setup FastText tool
            self.fasttext_tool.setup()
            logger.info("FastText tool initialized successfully")

        except Exception as e:
            logger.error(f"Error setting up classification agent: {str(e)}")
            raise

    def classify_email(self, email, method: str = "llm") -> Dict[str, Any]:
        """
        Classify an email using the specified method
        
        Args:
            email: The email to classify
            method: Classification method ('llm', 'bert', 'fasttext')
            
        Returns:
            Classification result dictionary
        """
        try:
            tool_map = {
                "llm": self.llm_tool,
                "bert": self.bert_tool,
                "fasttext": self.fasttext_tool
            }

            tool = tool_map.get(method.lower())
            if not tool:
                raise ValueError(f"Unknown classification method: {method}")

            result = tool(email)
            logger.info(f"Classification result using {method}: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in email classification: {str(e)}")
            return {
                "classification": "unknown",
                "confidence": 0.0,
                "explanation": f"Error: {str(e)}"
            } 