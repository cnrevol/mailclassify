from typing import Dict, Any, Optional
from .llm_factory import LLMFactory
import logging
import json
from django.conf import settings

logger = logging.getLogger('core')

class ChatService:
    """
    Chat service for handling chat interactions
    """
    def __init__(self):
        # 默认使用azure provider
        self.default_provider = 'azure'
        # 默认使用ID为1的LLM实例
        self.default_instance_id = 1

    def _parse_model_string(self, model: str) -> tuple[str, int]:
        """Parse model string to get provider and instance id"""
        if not model:
            return self.default_provider, self.default_instance_id

        # Expected format: 'provider-name' or 'provider-name-id'
        parts = model.split('-')
        if len(parts) < 2:
            return self.default_provider, self.default_instance_id

        provider = parts[0]
        # Try to get instance id from the last part
        try:
            instance_id = int(parts[-1])
        except ValueError:
            instance_id = self.default_instance_id

        return provider, instance_id

    def process_message(self, message: str, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a chat message and return the response
        """
        try:
            # Parse model string to get provider and instance id
            provider, instance_id = self._parse_model_string(model or '')
            logger.info(f"Using LLM provider: {provider}, instance: {instance_id}")

            # Get LLM instance
            llm = LLMFactory.get_instance_by_id(provider, instance_id)
            if not llm:
                return {
                    'status': 'error',
                    'message': 'Failed to initialize LLM instance'
                }

            # Get completion from LLM
            response = llm.get_completion(message)
            if response is None:
                return {
                    'status': 'error',
                    'message': 'Failed to get response from LLM'
                }

            # Parse response content
            content_type = 'text'
            if response.startswith('```') or '<table>' in response:
                content_type = 'markdown' if response.startswith('```') else 'html'

            return {
                'status': 'success',
                'content': response,
                'content_type': content_type
            }

        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error processing message: {str(e)}'
            }

    def format_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the response for frontend display
        """
        return {
            'success': response['status'] == 'success',
            'data': {
                'content': response['content'],
                'type': response.get('content_type', 'text')
            } if response['status'] == 'success' else None,
            'error': response.get('message') if response['status'] == 'error' else None
        } 