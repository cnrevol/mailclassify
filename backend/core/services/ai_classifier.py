import json
import logging
import os
from typing import Dict, Any, List, Optional
from smolagents import Tool
from django.conf import settings
from django.apps import apps
from decouple import config
import os.path  # 仅用于路径拼接

# Import models through Django's app registry
CCEmail = apps.get_model('core', 'CCEmail')

# Import from core package
from core.llm_factory import LLMFactory
from core.model_providers import BertProvider, FastTextProvider

logger = logging.getLogger(__name__)

class EmailClassificationTool(Tool):
    """Base class for email classification tools"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.inputs = {
            "email": {
                "description": "The email object to classify",
                "type": "object",
                "required": True
            }
        }
        # 使用 AUTHORIZED_TYPES 中的值
        self.output_type = "object"
        self.available_categories: List[str] = []  # Will be set by the agent
        super().__init__(name=name, description=description)
        logger.debug(f"Initialized EmailClassificationTool: {name}")

    def set_categories(self, categories: List[str]) -> None:
        """Set available categories for classification"""
        self.available_categories = categories
        logger.debug(f"Set categories: {categories}")
        
    def forward(self, email) -> Dict[str, Any]:
        """
        分类邮件的基础方法，需要在子类中实现
        """
        raise NotImplementedError("Subclasses must implement this method")

class LLMClassificationTool(EmailClassificationTool):
    """Tool for classifying emails using LLM"""
    def __init__(self):
        super().__init__(
            name="llm_classify",
            description="Classify emails using LLM based on content analysis and pattern recognition"
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

    def forward(self, email) -> Dict[str, Any]:
        """Classify email using LLM"""
        try:
            if not self.llm_provider:
                raise ValueError("LLM provider not initialized")

            # 提取邮件内容
            subject = email.subject or ""
            body = email.content or ""  # 使用 content 而不是 body
            sender = email.sender or ""
            
            # 构建系统消息和用户消息
            system_message = {
                "role": "system",
                "content": f"你是一个邮件分类助手。请将邮件分类到以下类别之一：{', '.join(self.available_categories)}。请以JSON格式返回结果，包含以下字段：classification（分类结果）、confidence（置信度，0-1之间的数值）和explanation（分类理由的简短解释）。"
            }
            
            user_message = {
                "role": "user",
                "content": f"请分析以下邮件内容：\n\n发件人: {sender}\n主题: {subject}\n内容:\n{body[:1000]}..."
            }
            
            # 发送消息到 LLM
            messages = [system_message, user_message]
            logger.info(f"Sending messages to LLM: {messages}")
            
            # 获取LLM响应
            response = self.llm_provider.chat(messages)
            if not response:
                raise ValueError("No response from LLM")
            
            # 解析响应
            try:
                result = json.loads(response)
                logger.info(f"LLM classification result: {result}")
                return result
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {response}")
                return {
                    "classification": self.available_categories[0] if self.available_categories else "unknown",
                    "confidence": 0.5,
                    "explanation": f"Error parsing LLM response: {response[:100]}..."
                }
                
        except Exception as e:
            logger.error(f"Error in LLM classification: {str(e)}")
            return {
                "classification": self.available_categories[0] if self.available_categories else "unknown",
                "confidence": 0.0,
                "explanation": f"Error: {str(e)}"
            }

class BertClassificationTool(EmailClassificationTool):
    """Tool for classifying emails using BERT"""
    def __init__(self):
        super().__init__(
            name="bert_classify",
            description="Classify emails using BERT model with pre-trained language understanding"
        )
        self.model_provider = None

    def setup(self) -> None:
        """Setup BERT model"""
        try:
            # 使用 decouple.config 获取模型路径
            bert_model_path = config('BERT_MODEL_PATH', default='./models/bert')
            
            # 检查路径是否存在且可访问
            if not os.path.exists(bert_model_path):
                logger.error(f"BERT model path does not exist: {bert_model_path}")
                return
                
            # 检查权限
            try:
                with open(os.path.join(bert_model_path, 'test_access.tmp'), 'w') as f:
                    f.write('test')
                os.remove(os.path.join(bert_model_path, 'test_access.tmp'))
            except PermissionError:
                logger.error(f"Permission denied for BERT model path: {bert_model_path}")
                logger.error("Please check file permissions or run the application with appropriate privileges")
                return
            except Exception as e:
                logger.warning(f"Could not verify write permissions: {str(e)}")
            
            # 创建配置字典
            config_dict = {
                'tokenizer_path': bert_model_path,
                'model_path': bert_model_path  # 使用同一路径，让 BertProvider 自己处理文件名
            }
            
            logger.info(f"Using BERT model path: {bert_model_path}")
            self.model_provider = BertProvider(config_dict)
            self.model_provider.initialize()
            logger.info("BERT model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize BERT model: {str(e)}")

    def forward(self, email) -> Dict[str, Any]:
        """Classify email using BERT"""
        try:
            if not self.model_provider:
                raise ValueError("BERT model not initialized")

            # 提取邮件内容
            subject = email.subject or ""
            body = email.content or ""  # 使用 content 而不是 body
            
            # 构建消息
            message = [{
                "role": "user",
                "content": f"Subject: {subject}\n\nBody: {body[:1000]}"
            }]
            
            # 获取分类结果
            response = self.model_provider.chat(message)
            if not response:
                raise ValueError("No response from BERT model")
            
            # 解析响应
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # 如果不是有效的JSON，创建一个默认结果
                result = {
                    "classification": self.available_categories[0] if self.available_categories else "unknown",
                    "confidence": 0.5,
                    "explanation": f"Failed to parse response: {response[:100]}..."
                }
                
            logger.info(f"BERT classification result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in BERT classification: {str(e)}")
            return {
                "classification": self.available_categories[0] if self.available_categories else "unknown",
                "confidence": 0.0,
                "explanation": f"Error: {str(e)}"
            }

class FastTextClassificationTool(EmailClassificationTool):
    """Tool for classifying emails using FastText"""
    def __init__(self):
        super().__init__(
            name="fasttext_classify",
            description="Classify emails using FastText model for efficient text classification"
        )
        self.model_provider = None

    def setup(self) -> None:
        """Setup FastText model"""
        try:
            # 使用 decouple.config 获取模型路径
            fasttext_model_path = config('FASTTEXT_MODEL_PATH', default='./models/fasttext/model.bin')
            
            # 检查文件是否存在
            if not os.path.isfile(fasttext_model_path):
                logger.error(f"FastText model file does not exist: {fasttext_model_path}")
                return
                
            # 检查权限
            try:
                with open(fasttext_model_path, 'rb') as f:
                    # 只读取一小部分来测试访问权限
                    _ = f.read(10)
            except PermissionError:
                logger.error(f"Permission denied for FastText model file: {fasttext_model_path}")
                logger.error("Please check file permissions or run the application with appropriate privileges")
                return
            except Exception as e:
                logger.warning(f"Could not verify read permissions: {str(e)}")
            
            # 创建配置字典
            config_dict = {
                'model_path': fasttext_model_path
            }
            
            logger.info(f"Using FastText model path: {fasttext_model_path}")
            self.model_provider = FastTextProvider(config_dict)
            self.model_provider.initialize()
            logger.info("FastText model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize FastText model: {str(e)}")

    def forward(self, email) -> Dict[str, Any]:
        """Classify email using FastText"""
        try:
            if not self.model_provider:
                raise ValueError("FastText model not initialized")

            # 提取邮件内容
            subject = email.subject or ""
            body = email.content or ""  # 使用 content 而不是 body
            
            # 构建消息
            message = [{
                "role": "user",
                "content": f"Subject: {subject}\n\nBody: {body[:1000]}"
            }]
            
            # 获取分类结果
            response = self.model_provider.chat(message)
            if not response:
                raise ValueError("No response from FastText")
            
            # 解析响应
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # 如果不是有效的JSON，创建一个默认结果
                result = {
                    "classification": self.available_categories[0] if self.available_categories else "unknown",
                    "confidence": 0.5,
                    "explanation": f"Failed to parse response: {response[:100]}..."
                }
                
            logger.info(f"FastText classification result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in FastText classification: {str(e)}")
            return {
                "classification": self.available_categories[0] if self.available_categories else "unknown",
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

            result = tool.forward(email)
            logger.info(f"Classification result using {method}: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in email classification: {str(e)}")
            return {
                "classification": "unknown",
                "confidence": 0.0,
                "explanation": f"Error: {str(e)}"
            } 