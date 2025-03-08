import os
import logging
from typing import Dict, Any, Optional, List
import torch
from transformers import BertTokenizer
import fasttext
from django.conf import settings
from decouple import config
# from azure.storage.blob import BlobServiceClient
from .base_providers import LLMProvider
import json
from . import train_bert__core
from .train_bert__core import BertClassifier 


logger = logging.getLogger('core')

class BertProvider(LLMProvider):
    """BERT模型提供者"""
    def initialize(self) -> bool:
        try:
            # 获取模型路径，优先使用配置中的路径，然后使用环境变量中的路径
            tokenizer_path = self.config.get('tokenizer_path')
            if not tokenizer_path:
                tokenizer_path = config('BERT_MODEL_PATH', default='./models/bert')
                
            model_path = self.config.get('model_path')
            if not model_path:
                model_path = os.path.join(tokenizer_path, 'clf_bert_weights_en.pt')

            # 如果使用Azure存储，下载模型
            # if settings.AZURE_STORAGE_CONNECTION_STRING:
            #     model_path = self._download_from_azure(model_path)
            #     tokenizer_path = os.path.dirname(model_path)

            logger.info(f"Loading BERT model from {model_path}")
            logger.info(f"Using tokenizer from {tokenizer_path}")

            # 加载分词器和模型
            self.tokenizer = BertTokenizer.from_pretrained(tokenizer_path)
            
            # 加载标签映射
            labels_path = os.path.join(os.path.dirname(model_path), 'labels.json')
            if os.path.exists(labels_path):
                with open(labels_path, 'r', encoding='utf-8') as f:
                    self.labels = json.load(f)
                    self.labels_reverse = {v: k for k, v in self.labels.items()}
            else:
                # 默认标签
                self.labels = {"work": 0, "personal": 1, "spam": 2, "other": 3}
                self.labels_reverse = {0: "work", 1: "personal", 2: "spam", 3: "other"}
                
            # 初始化模型
            self.model = BertClassifier('bert-base-uncased', len(self.labels))
            self.model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
            self.model.eval()
            
            logger.info("BERT model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading BERT model: {str(e)}")
            return False

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """使用BERT模型进行对话"""
        try:
            # 获取最后一条用户消息
            user_message = next((msg['content'] for msg in reversed(messages) 
                               if msg['role'] == 'user'), None)
            if not user_message:
                return None

            # 使用模型进行预测
            inputs = self.tokenizer(user_message, 
                                  return_tensors="pt",
                                  truncation=True,
                                  max_length=512,
                                  padding=True)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.softmax(outputs.logits, dim=1)
                predicted_class = torch.argmax(predictions).item()
                confidence = predictions[0][predicted_class].item()

            # 返回预测结果
            result = {
                "classification": str(predicted_class),
                "confidence": float(confidence),
                "explanation": f"BERT model prediction with confidence {confidence:.2f}"
            }
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error in BERT chat: {str(e)}")
            return None

    def _download_from_azure(self, model_path: str) -> str:
        """从Azure存储下载模型"""
        try:
            # 创建本地临时目录
            local_path = os.path.join(settings.BASE_DIR, 'models_cache')
            os.makedirs(local_path, exist_ok=True)
            
            # 获取blob名称
            blob_name = os.path.basename(model_path)
            local_file_path = os.path.join(local_path, blob_name)
            
            # 如果本地已存在，直接返回
            if os.path.exists(local_file_path):
                return local_file_path
            
            # 下载文件
            # blob_service_client = BlobServiceClient.from_connection_string(
            #     settings.AZURE_STORAGE_CONNECTION_STRING
            # )
            # container_client = blob_service_client.get_container_client(
            #     settings.AZURE_STORAGE_CONTAINER
            # )
            
            with open(local_file_path, "wb") as file:
                blob_data = container_client.download_blob(blob_name)
                blob_data.readinto(file)
            
            logger.info(f"Downloaded model from Azure: {blob_name}")
            return local_file_path
            
        except Exception as e:
            logger.error(f"Error downloading model from Azure: {str(e)}")
            raise

class FastTextProvider(LLMProvider):
    """FastText模型提供者"""
    def initialize(self) -> bool:
        try:
            # 获取模型路径，优先使用配置中的路径，然后使用环境变量中的路径
            model_path = self.config.get('model_path')
            if not model_path:
                model_path = config('FASTTEXT_MODEL_PATH', default='./models/fasttext/model.bin')

            # 如果使用Azure存储，下载模型
            # if settings.AZURE_STORAGE_CONNECTION_STRING:
            #     model_path = self._download_from_azure(model_path)

            logger.info(f"Loading FastText model from {model_path}")
            
            # 加载模型
            self.model = fasttext.load_model(model_path)
            
            logger.info("FastText model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading FastText model: {str(e)}")
            return False

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """使用FastText模型进行分类"""
        try:
            if not hasattr(self, 'model') or self.model is None:
                logger.error("FastText model not initialized")
                return None
                
            # 提取用户消息
            user_message = ""
            for message in messages:
                if message.get('role') == 'user':
                    user_message += message.get('content', '') + " "
            
            if not user_message.strip():
                logger.warning("Empty user message")
                return json.dumps({
                    "classification": "unknown",
                    "confidence": 0.0,
                    "explanation": "Empty message"
                })
            
            # 使用模型进行预测
            try:
                predictions = self.model.predict(user_message)
                if isinstance(predictions, tuple) and len(predictions) >= 2:
                    predicted_class = predictions[0][0].replace('__label__', '')
                    confidence = float(predictions[1][0])
                else:
                    logger.warning(f"Unexpected prediction format: {predictions}")
                    predicted_class = "unknown"
                    confidence = 0.0
            except Exception as e:
                logger.error(f"Error during prediction: {str(e)}")
                predicted_class = "unknown"
                confidence = 0.0
            
            # 返回预测结果
            result = {
                "classification": predicted_class,
                "confidence": confidence,
                "explanation": f"FastText classified as '{predicted_class}' with confidence {confidence:.2f}"
            }
            
            return json.dumps(result)
            
        except Exception as e:
            logger.error(f"Error in FastText chat: {str(e)}")
            return None

    def _download_from_azure(self, model_path: str) -> str:
        """从Azure存储下载模型"""
        try:
            # 创建本地临时目录
            local_path = os.path.join(settings.BASE_DIR, 'models_cache')
            os.makedirs(local_path, exist_ok=True)
            
            # 获取blob名称
            blob_name = os.path.basename(model_path)
            local_file_path = os.path.join(local_path, blob_name)
            
            # 如果本地已存在，直接返回
            if os.path.exists(local_file_path):
                return local_file_path
            
            # 下载文件
            # blob_service_client = BlobServiceClient.from_connection_string(
            #     settings.AZURE_STORAGE_CONNECTION_STRING
            # )
            # container_client = blob_service_client.get_container_client(
            #     settings.AZURE_STORAGE_CONTAINER
            # )
            
            with open(local_file_path, "wb") as file:
                blob_data = container_client.download_blob(blob_name)
                blob_data.readinto(file)
            
            logger.info(f"Downloaded model from Azure: {blob_name}")
            return local_file_path
            
        except Exception as e:
            logger.error(f"Error downloading model from Azure: {str(e)}")
            raise 