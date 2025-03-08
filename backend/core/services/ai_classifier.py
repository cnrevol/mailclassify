import json
import logging
import os
import re
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

def extract_text_from_html(html_content: str) -> str:
    """
    从 HTML 内容中提取纯文本
    
    Args:
        html_content: HTML 格式的内容
        
    Returns:
        提取的纯文本
    """
    if not html_content:
        return ""
        
    # 移除 HTML 标签
    text = re.sub(r'<[^>]+>', ' ', html_content)
    
    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    
    # 移除特殊字符和转义序列
    text = text.replace('\\r', ' ').replace('\\n', ' ').replace('\\t', ' ')
    
    # 移除引号
    text = text.replace('"', '').replace("'", "")
    
    # 移除多余的空格
    text = text.strip()
    
    return text

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
            content = email.content or ""  # 使用 content 而不是 body
            sender = email.sender or ""
            
            # 提取纯文本内容
            clean_content = extract_text_from_html(content)
            logger.debug(f"提取的纯文本内容: {clean_content[:100]}...")
            
            # 构建系统消息和用户消息
            system_message = {
                "role": "system",
                "content": f"你是一个邮件分类助手。请将邮件分类到以下类别之一：{', '.join(self.available_categories)}。请以JSON格式返回结果，包含以下字段：classification（分类结果）、confidence（置信度，0-1之间的数值）和explanation（分类理由的简短解释）。"
            }
            
            user_message = {
                "role": "user",
                "content": f"请分析以下邮件内容：\n\n发件人: {sender}\n主题: {subject}\n内容:\n{clean_content[:1000]}..."
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
            content = email.content or ""  # 使用 content 而不是 body
            
            # 提取纯文本内容
            clean_content = extract_text_from_html(content)
            logger.debug(f"提取的纯文本内容: {clean_content[:100]}...")
            
            # 构建消息
            message = [{
                "role": "user",
                "content": f"Subject: {subject}\n\nBody: {clean_content[:1000]}"
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
            content = email.content or ""  # 使用 content 而不是 body
            
            # 提取纯文本内容
            clean_content = extract_text_from_html(content)
            logger.debug(f"提取的纯文本内容: {clean_content[:100]}...")
            
            # 构建消息 - 确保没有换行符
            clean_text = f"Subject: {subject} Body: {clean_content}".replace('\n', ' ').replace('\r', ' ')
            message = [{
                "role": "user",
                "content": clean_text
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

class ClassifierFactory:
    """分类器工厂，用于创建和管理不同类型的分类器"""
    
    _instance = None
    _classifiers = {}
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = ClassifierFactory()
        return cls._instance
    
    def get_classifier(self, method: str, categories: List[str]):
        """
        获取指定类型的分类器
        
        Args:
            method: 分类方法 ('llm', 'bert', 'fasttext')
            categories: 可用的分类类别
            
        Returns:
            分类器实例
        """
        # 如果分类器已经存在，直接返回
        if method in self._classifiers:
            # 更新分类类别
            self._classifiers[method].set_categories(categories)
            return self._classifiers[method]
        
        # 创建新的分类器
        if method == 'llm':
            classifier = LLMClassificationTool()
        elif method == 'bert':
            classifier = BertClassificationTool()
        elif method == 'fasttext':
            classifier = FastTextClassificationTool()
        else:
            raise ValueError(f"Unknown classification method: {method}")
        
        # 设置分类类别
        classifier.set_categories(categories)
        
        # 初始化分类器
        classifier.setup()
        
        # 缓存分类器
        self._classifiers[method] = classifier
        
        return classifier
    
    def classify_email(self, email, method: str, categories: List[str]) -> Dict[str, Any]:
        """
        使用指定方法对邮件进行分类
        
        Args:
            email: 要分类的邮件
            method: 分类方法 ('llm', 'bert', 'fasttext')
            categories: 可用的分类类别
            
        Returns:
            分类结果字典
        """
        try:
            # 获取分类器
            classifier = self.get_classifier(method, categories)
            
            # 使用分类器进行分类
            result = classifier.forward(email)
            
            # 获取分类结果
            classification = result.get('classification', 'unclassified')
            logger.info(f"邮件 '{email.subject[:50]}...' 被 {method} 分类为 '{classification}'")
            
            return {
                'classification': classification,
                'rule_name': f"{method.upper()} Classification",
                'explanation': result.get('explanation', 'No explanation provided')
            }
            
        except Exception as e:
            logger.error(f"{method} 分类过程中出错: {str(e)}", exc_info=True)
            return {
                'classification': 'unclassified',
                'rule_name': f"{method.upper()} Classification",
                'explanation': f"Error during classification: {str(e)}"
            }

class EmailClassificationAgent:
    """Agent for email classification using multiple models"""
    def __init__(self, categories: List[str]):
        self.categories = categories
        self.factory = ClassifierFactory.get_instance()
        self.is_initialized = True
        
    def setup(self, llm_provider: str = "azure", llm_instance_id: int = 1) -> None:
        """Setup is now handled by the ClassifierFactory"""
        pass
        
    def classify_email(self, email, method: str = "llm") -> Dict[str, Any]:
        """
        Classify email using specified method
        
        Args:
            email: The email to classify
            method: Classification method ('llm', 'bert', 'fasttext')
            
        Returns:
            Classification result dictionary
        """
        return self.factory.classify_email(email, method, self.categories) 