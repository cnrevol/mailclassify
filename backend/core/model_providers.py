import os
import logging
from typing import Dict, Any, Optional, List
import torch
from transformers import BertTokenizer
import fasttext
from django.conf import settings
# from azure.storage.blob import BlobServiceClient
from .base_providers import LLMProvider
import json

logger = logging.getLogger('core')

class BertProvider(LLMProvider):
    """BERT模型提供者"""
    def initialize(self) -> bool:
        try:
            # 获取模型路径
            tokenizer_path = self.config.get('tokenizer_path', settings.BERT_MODEL_PATH)
            model_path = self.config.get('model_path', 
                os.path.join(tokenizer_path, 'clf_bert_weights_en.pt'))

            # 如果使用Azure存储，下载模型
            # if settings.AZURE_STORAGE_CONNECTION_STRING:
            #     model_path = self._download_from_azure(model_path)
            #     tokenizer_path = os.path.dirname(model_path)

            logger.info(f"Loading BERT model from {model_path}")
            
            # 加载tokenizer和模型
            self.tokenizer = BertTokenizer.from_pretrained(tokenizer_path)
            self.model = torch.load(model_path, map_location="cpu")
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
            # 获取模型路径
            model_path = self.config.get('model_path', settings.FASTTEXT_MODEL_PATH)
            
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
        """使用FastText模型进行对话"""
        try:
            # 获取最后一条用户消息
            user_message = next((msg['content'] for msg in reversed(messages) 
                               if msg['role'] == 'user'), None)
            if not user_message:
                return None

            # 使用模型进行预测
            predictions = self.model.predict(user_message)
            predicted_class = predictions[0][0].replace('__label__', '')
            confidence = float(predictions[1][0])

            # 返回预测结果
            result = {
                "classification": predicted_class,
                "confidence": confidence,
                "explanation": f"FastText model prediction with confidence {confidence:.2f}"
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