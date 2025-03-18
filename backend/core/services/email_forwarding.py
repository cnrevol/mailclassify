import logging
from typing import Dict, List, Any, Optional
from django.conf import settings
from django.utils import timezone
from ..models import (
    CCForwardingRule,
    CCForwardingAddress,
    CCEmailForwardingLog,
    CCEmail,
    CCEmailMonitorStatus,
    CCUserMailInfo
)
from django.db import connection, transaction
from ..sclogging import WebSocketLogger
from .graph_service import GraphService
from .mail_service import OutlookMailService
from .email_classifier import EmailClassifier
from concurrent.futures import ThreadPoolExecutor

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
    
    def __init__(self, email: str):
        self.email = email
        self.logger = WebSocketLogger(__name__, email)
    
    @classmethod
    def process_classified_emails(cls, classification_results: Dict[str, List[Dict[str, Any]]], mail_service) -> List[Dict[str, Any]]:
        """
        处理已分类的邮件，根据分类结果进行转发
        
        Args:
            classification_results: 分类结果字典，键为分类名称，值为邮件列表
            mail_service: 邮件服务实例，用于转发邮件
            
        Returns:
            处理结果列表
        """
        service = cls(mail_service.user_mail.email)
        # 创建 GraphService 实例
        graph_service = GraphService(mail_service.user_mail)
        return service._process_classified_emails(classification_results, graph_service)
        
    def _process_classified_emails(self, classification_results: Dict[str, List[Dict[str, Any]]], graph_service) -> List[Dict[str, Any]]:
        """处理已分类邮件的内部方法"""
        processing_results = []
        
        # 遍历所有分类
        for classification, emails_data in classification_results.items():
            self.logger.info(f"处理分类 '{classification}' 的 {len(emails_data)} 封邮件")
            
            # 获取对应的 email_types
            email_types = settings.EMAIL_TYPE_MAPPING.get(classification.lower(), [])
            self.logger.debug(f"映射的邮件类型: {email_types}")
            
            if not email_types:
                self.logger.warning(f"分类 '{classification}' 没有映射的邮件类型")
                continue
            
            # 处理每封邮件
            for email_data in emails_data:
                email = email_data['email']
                
                # 检查邮件是否已经被转发
                if email.is_forwarded:
                    self.logger.info(f"邮件已经被转发过，跳过: {email.subject}")
                    continue
                
                # 对每个 email_type 进行处理
                forwarded = False  # 标记邮件是否在当前循环中被成功转发
                for email_type in email_types:
                    # 如果邮件已经在当前循环中被转发，跳过后续的 email_type
                    if forwarded:
                        self.logger.debug(f"邮件已经被转发，跳过其他邮件类型: {email_type}")
                        continue
                        
                    self.logger.info(f"处理邮件类型: {email_type}, 邮件: {email.subject}")
                    
                    # 获取转发信息
                    self.logger.debug("获取转发信息")
                    forwarding_info = self.get_forwarding_info(
                        email_content=email.content,
                        email_type=email_type
                    )
                    
                    if forwarding_info.get('success'):
                        # 转发邮件
                        self.logger.info(f"转发邮件到: {forwarding_info['forward_addresses']}")
                        try:
                            forward_result = graph_service.forward_email(
                                email_id=email.message_id,
                                to_recipients=forwarding_info['forward_addresses'],
                                forward_comment=forwarding_info['forward_message']
                            )
                            
                            if forward_result.get('success'):
                                # 创建日志条目
                                self.logger.debug("在数据库中创建日志条目")
                                
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
                                
                                # 更新邮件的转发状态和处理时间
                                email.is_forwarded = True
                                email.processed_time = timezone.now()
                                email.save(update_fields=['is_forwarded', 'processed_time'])
                                forwarded = True  # 标记邮件已被成功转发
                                
                                self.logger.debug(f"创建的日志条目 ID: {log_entry.id}")
                                processing_results.append({
                                    'id': log_entry.id,
                                    'title': log_entry.title,
                                    'sender': log_entry.sender,
                                    'received_time': log_entry.received_time,
                                    'classification': log_entry.classification,
                                    'email_type': log_entry.email_type,
                                    'forwarding_recipient': log_entry.forwarding_recipient,
                                    'created_at': log_entry.created_at,
                                    'message_id': email.message_id
                                })
                                self.logger.info(f"成功处理并转发邮件: {email.subject}")
                            else:
                                self.logger.error(f"转发邮件失败: {forward_result.get('error')}")
                        except Exception as e:
                            self.logger.error(f"转发邮件时出错: {str(e)}", exc_info=True)
                    else:
                        self.logger.warning(f"无法获取邮件的转发信息: {email.subject}, 错误: {forwarding_info.get('error')}")
        
        return processing_results
    
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

def check_new_emails(cls, email: str, check_interval_minutes: int = 5) -> dict:
    """
    检查并处理新邮件
    
    Args:
        email: 邮箱地址
        check_interval_minutes: 检查间隔（分钟）
        
    Returns:
        dict: 处理结果
    """
    service = cls(email)
    
    try:
        # 获取监控状态
        monitor_status = CCEmailMonitorStatus.objects.filter(email=email).first()
        if not monitor_status or not monitor_status.is_monitoring:
            service.logger.info(f"邮箱 {email} 未开启监控，跳过检查")
            return {'status': 'skipped', 'reason': 'monitoring_not_active'}
        
        # 获取邮箱配置
        user_mail = CCUserMailInfo.objects.filter(email=email, is_active=True).first()
        if not user_mail:
            service.logger.error(f"未找到邮箱配置: {email}")
            return {'status': 'error', 'error': 'email_config_not_found'}
        
        # 计算需要检查的时间范围
        now = timezone.now()
        if monitor_status.last_check_time:
            time_diff = (now - monitor_status.last_check_time).total_seconds() / 60
            if time_diff < check_interval_minutes:
                service.logger.debug(f"距离上次检查时间 {time_diff:.1f} 分钟，未达到检查间隔 {check_interval_minutes} 分钟，跳过")
                return {'status': 'skipped', 'reason': 'check_interval_not_reached'}
            hours = max(time_diff / 60, 0.5)  # 至少获取30分钟内的邮件
        else:
            hours = 2
        
        # 从 Outlook 获取未处理的新邮件
        service.logger.info(f"开始从 Outlook: {email} 检查是否有新的邮件。")
        mail_service = OutlookMailService(user_mail)
        
        # 使用事务和锁确保邮件状态的一致性
        with transaction.atomic():
            # 获取新邮件，并立即标记为已处理状态，避免重复处理
            new_emails = []
            fetched_emails = mail_service.fetch_emails(hours=int(hours))
            
            for email_obj in fetched_emails:
                # 检查邮件是否已存在且未处理
                existing_email = CCEmail.objects.select_for_update().filter(
                    message_id=email_obj.message_id,
                    is_processed=False
                ).first()
                
                if existing_email:
                    new_emails.append(existing_email)
                    # 标记为处理中状态
                    existing_email.is_processed = True
                    existing_email.save(update_fields=['is_processed'])
        
        if not new_emails:
            service.logger.info("没有新邮件需要分类")
            return {'status': 'success', 'message': '没有新邮件需要分类'}
        
        # 使用线程池并发处理邮件
        with ThreadPoolExecutor(max_workers=3) as executor:
            # 创建处理任务
            futures = []
            for email_obj in new_emails:
                future = executor.submit(
                    service._process_single_email,
                    email_obj,
                    settings.DEFAULT_EMAIL_CLASSIFICATION_METHOD
                )
                futures.append((email_obj, future))
            
            # 等待所有任务完成并收集结果
            results = {}
            for email_obj, future in futures:
                try:
                    result = future.result()
                    if result:
                        classification = result.get('classification', 'unclassified')
                        if classification not in results:
                            results[classification] = []
                        results[classification].append({
                            'email': email_obj,
                            'confidence': result.get('confidence', 0.0),
                            'rule_name': result.get('rule_name', ''),
                            'explanation': result.get('explanation', '')
                        })
                except Exception as e:
                    service.logger.error(f"处理邮件时出错: {str(e)}", exc_info=True)
                    if 'error' not in results:
                        results['error'] = []
                    results['error'].append({
                        'email': email_obj,
                        'error': str(e)
                    })
        
        # 处理转发
        if results:
            service.logger.info("开始处理邮件转发")
            forwarding_results = EmailForwardingService.process_classified_emails(
                classification_results=results,
                mail_service=mail_service
            )
        
        # 更新监控状态
        monitor_status.last_check_time = now
        monitor_status.last_found_emails = len(new_emails)
        monitor_status.total_classified_emails += len(new_emails)
        monitor_status.save()
        
        return {
            'status': 'success',
            'message': f'成功处理 {len(new_emails)} 封邮件',
            'results': results
        }
        
    except Exception as e:
        service.logger.error(f"检查新邮件失败: {str(e)}", exc_info=True)
        return {'status': 'error', 'error': str(e)}

def _process_single_email(self, email: CCEmail, method: str) -> Dict[str, Any]:
    """处理单个邮件"""
    try:
        # 使用事务确保处理的原子性
        with transaction.atomic():
            # 再次检查邮件状态
            email.refresh_from_db()
            if email.is_forwarded:
                self.logger.info(f"邮件已被处理，跳过: {email.subject}")
                return None
            
            # 进行分类
            result = EmailClassifier.classify_single_email(
                email=email,
                method=method,
                ws_logger=self.logger
            )
            
            # 更新邮件分类信息
            email.categories = result.get('classification', 'unclassified')
            email.classification_confidence = result.get('confidence', 0.0)
            email.classification_reason = result.get('explanation', '')
            email.classification_rule = result.get('rule_name', '')
            email.classification_method = method
            email.save()
            
            return result
            
    except Exception as e:
        self.logger.error(f"处理邮件时出错: {str(e)}", exc_info=True)
        return None 