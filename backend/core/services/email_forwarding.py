import logging
from typing import Dict, List, Any, Optional
from django.conf import settings
from django.utils import timezone
from ..models import CCForwardingRule, CCForwardingAddress, CCEmailForwardingLog
from django.db import connection

logger = logging.getLogger(__name__)

class TaskAssignmentService:
    """任务分配服务，用于平均分配任务"""
    
    @staticmethod
    def get_optimal_address(addresses, task_type: str):
        """
        获取最优的地址进行任务分配
        
        Args:
            addresses: 可用的地址列表
            task_type: 任务类型
            
        Returns:
            最优的地址
        """
        # 简单实现：返回第一个地址
        # 在实际应用中，可以根据历史分配情况、工作负载等因素进行更复杂的分配
        return addresses.first()

class EmailForwardingService:
    """邮件转发服务"""
    
    @staticmethod
    def get_forwarding_info(email_content: str, email_type: str) -> dict:
        """
        根据邮件类型和内容获取转发信息
        
        Args:
            email_content: 邮件内容
            email_type: 邮件类型
            
        Returns:
            转发信息字典，包括地址、消息和优先级
        """
        try:
            # 获取此邮件类型的活动转发规则
            rule = CCForwardingRule.objects.filter(
                email_type=email_type,
                is_active=True
            ).prefetch_related('addresses').first()
            
            if not rule:
                return {
                    'success': False,
                    'error': f'未找到邮件类型的活动转发规则: {email_type}'
                }
            
            # 获取活动的转发地址
            addresses = rule.addresses.filter(is_active=True)
            if not addresses.exists():
                return {
                    'success': False,
                    'error': f'未找到规则的活动转发地址: {rule.name}'
                }
            
            # 如果规则类型是 'A'（平均分配），获取最优地址
            if rule.rule_type == 'A':
                address = TaskAssignmentService.get_optimal_address(
                    addresses=addresses,
                    task_type=email_type
                )
                forward_addresses = [{'email': address.email, 'name': address.name}]
            else:  # 对于规则类型 'B'（直接转发）
                forward_addresses = [
                    {'email': addr.email, 'name': addr.name}
                    for addr in addresses
                ]
            
            return {
                'success': True,
                'rule_type': rule.rule_type,
                'forward_addresses': forward_addresses,
                'forward_message': rule.forward_message,
                'priority': rule.priority,
                'rule_name': rule.name
            }
            
        except Exception as e:
            logger.error(f"获取转发信息时出错: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'处理转发请求时出错: {str(e)}'
            }
    
    @staticmethod
    def process_classified_emails(classification_results: Dict[str, List[Dict[str, Any]]], graph_service) -> List[Dict[str, Any]]:
        """
        处理已分类的邮件，根据分类结果进行转发
        
        Args:
            classification_results: 分类结果字典，键为分类名称，值为邮件列表
            graph_service: Graph API 服务，用于转发邮件
            
        Returns:
            处理结果列表
        """
        processing_results = []
        
        # 遍历所有分类
        for classification, emails_data in classification_results.items():
            logger.info(f"处理分类 '{classification}' 的 {len(emails_data)} 封邮件")
            
            # 跳过 'error' 和 'unclassified' 分类
            if classification in ['error', 'unclassified']:
                logger.info(f"跳过 '{classification}' 分类的邮件")
                continue
            
            # 获取对应的 email_types
            email_types = settings.EMAIL_TYPE_MAPPING.get(classification.lower(), [])
            logger.debug(f"映射的邮件类型: {email_types}")
            
            if not email_types:
                logger.warning(f"分类 '{classification}' 没有映射的邮件类型")
                continue
            
            # 处理每封邮件
            for email_data in emails_data:
                email = email_data['email']
                
                # 对每个 email_type 进行处理
                for email_type in email_types:
                    logger.info(f"处理邮件类型: {email_type}, 邮件: {email.subject}")
                    
                    # 获取转发信息
                    logger.debug("获取转发信息")
                    forwarding_info = EmailForwardingService.get_forwarding_info(
                        email_content=email.content,
                        email_type=email_type
                    )
                    
                    if forwarding_info.get('success'):
                        # 转发邮件
                        logger.info(f"转发邮件到: {forwarding_info['forward_addresses']}")
                        try:
                            forward_result = graph_service.forward_email(
                                email_id=email.message_id,
                                to_recipients=forwarding_info['forward_addresses'],
                                forward_comment=forwarding_info['forward_message']
                            )
                            
                            # 创建日志条目
                            logger.debug("在数据库中创建日志条目")
                            
                            # 获取当前最大 ID 并加 1
                            with connection.cursor() as cursor:
                                cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM cc_email_forwarding_log")
                                next_id = cursor.fetchone()[0]
                            
                            log_entry = CCEmailForwardingLog.objects.create(
                                id=next_id,  # 手动设置 ID
                                title=email.subject,
                                sender=email.sender,
                                received_time=email.received_time,
                                classification=classification,
                                email_type=email_type,
                                forwarding_recipient=','.join([
                                    addr['email'] for addr in forwarding_info['forward_addresses']
                                ]),
                                message_id=email.message_id,
                                created_at=timezone.now()
                            )
                            
                            logger.debug(f"创建的日志条目 ID: {log_entry.id}")
                            processing_results.append({
                                'id': log_entry.id,
                                'title': log_entry.title,
                                'sender': log_entry.sender,
                                'received_time': log_entry.received_time,
                                'classification': log_entry.classification,
                                'email_type': log_entry.email_type,
                                'forwarding_recipient': log_entry.forwarding_recipient,
                                'created_at': log_entry.created_at
                            })
                            logger.info(f"成功处理并转发邮件: {email.subject}")
                        except Exception as e:
                            logger.error(f"转发邮件时出错: {str(e)}", exc_info=True)
                    else:
                        logger.warning(f"无法获取邮件的转发信息: {email.subject}, 错误: {forwarding_info.get('error')}")
        
        return processing_results 