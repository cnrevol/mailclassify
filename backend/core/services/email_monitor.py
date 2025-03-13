import logging
import time
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from ..models import CCUserMailInfo, CCEmailMonitorStatus, CCEmail
from .email_classifier import EmailClassifier
from .mail_service import OutlookMailService
from .email_forwarding import EmailForwardingService
from ..sclogging import WebSocketLogger

logger = logging.getLogger(__name__)

class EmailMonitorService:
    """邮件监控服务，用于定期检查和分类新邮件"""
    
    def __init__(self, email: str):
        """
        初始化邮件监控服务
        
        Args:
            email: 要监控的邮箱地址
        """
        self.email = email
        self.logger = WebSocketLogger(__name__, email)
    
    @classmethod
    def start_monitoring(cls, email: str) -> bool:
        """
        启动邮件监控
        
        Args:
            email: 要监控的邮箱地址
            
        Returns:
            是否成功启动监控
        """
        service = cls(email)
        return service._start_monitoring()
        
    def _start_monitoring(self) -> bool:
        """启动邮件监控的内部方法"""
        try:
            # 获取或创建监控状态
            status, created = CCEmailMonitorStatus.objects.get_or_create(
                email=self.email,
                defaults={'is_monitoring': True}
            )
            
            if not created:
                # 如果已存在，更新状态
                status.is_monitoring = True
                status.save(update_fields=['is_monitoring'])
            
            self.logger.info(f"开始监控邮箱: {self.email}")
            return True
            
        except Exception as e:
            self.logger.error(f"启动邮件监控时出错: {str(e)}", exc_info=True)
            return False
    
    @classmethod
    def stop_monitoring(cls, email: str) -> bool:
        """
        停止邮件监控
        
        Args:
            email: 要停止监控的邮箱地址
            
        Returns:
            是否成功停止监控
        """
        service = cls(email)
        return service._stop_monitoring()
        
    def _stop_monitoring(self) -> bool:
        """停止邮件监控的内部方法"""
        try:
            # 更新监控状态
            status = CCEmailMonitorStatus.objects.filter(email=self.email).first()
            if status:
                status.is_monitoring = False
                status.save(update_fields=['is_monitoring'])
                self.logger.info(f"停止监控邮箱: {self.email}")
                return True
            else:
                self.logger.warning(f"未找到邮箱的监控状态: {self.email}")
                return False
                
        except Exception as e:
            self.logger.error(f"停止邮件监控时出错: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    def get_monitoring_status(email: str) -> dict:
        """
        获取邮箱监控状态
        
        Args:
            email: 邮箱地址
            
        Returns:
            dict: 监控状态信息
        """
        try:
            monitor_status = CCEmailMonitorStatus.objects.filter(email=email).first()
            if monitor_status:
                return {
                    'email': monitor_status.email,
                    'is_monitoring': monitor_status.is_monitoring,
                    'last_check_time': monitor_status.last_check_time,
                    'last_found_emails': monitor_status.last_found_emails,
                    'total_classified_emails': monitor_status.total_classified_emails,
                    'updated_at': monitor_status.updated_at
                }
            else:
                return {
                    'email': email,
                    'is_monitoring': False,
                    'last_check_time': None,
                    'last_found_emails': 0,
                    'total_classified_emails': 0,
                    'updated_at': None
                }
                
        except Exception as e:
            logger.error(f"获取邮箱监控状态失败: {str(e)}", exc_info=True)
            return {
                'email': email,
                'is_monitoring': False,
                'error': str(e)
            }
    
    @classmethod
    def check_new_emails(cls, email: str, check_interval_minutes: int = 5) -> dict:
        """
        检查并处理新邮件
        
        Args:
            email: 邮箱地址
            check_interval_minutes: 检查间隔（分钟）
            
        Returns:
            dict: 处理结果
        """
        try:
            # 获取监控状态
            monitor_status = CCEmailMonitorStatus.objects.filter(email=email).first()
            if not monitor_status or not monitor_status.is_monitoring:
                logger.info(f"邮箱 {email} 未开启监控，跳过检查")
                return {'status': 'skipped', 'reason': 'monitoring_not_active'}
            
            # 获取邮箱配置
            user_mail = CCUserMailInfo.objects.filter(email=email, is_active=True).first()
            if not user_mail:
                logger.error(f"未找到邮箱配置: {email}")
                return {'status': 'error', 'error': 'email_config_not_found'}
            
            # 计算需要检查的时间范围
            now = timezone.now()
            if monitor_status.last_check_time:
                # 从上次检查时间开始
                time_diff = (now - monitor_status.last_check_time).total_seconds() / 60
                # 如果距离上次检查时间不足指定间隔，则跳过
                if time_diff < check_interval_minutes:
                    logger.debug(f"距离上次检查时间 {time_diff:.1f} 分钟，未达到检查间隔 {check_interval_minutes} 分钟，跳过")
                    return {'status': 'skipped', 'reason': 'check_interval_not_reached'}
                
                # 计算需要获取的邮件时间范围（小时）
                hours = max(time_diff / 60, 0.5)  # 至少获取30分钟内的邮件
            else:
                # 首次检查，获取最近2小时的邮件
                hours = 2
            
            # 从 Outlook 获取邮件
            # logger.info(f"开始从 Outlook 获取 {email} 的邮件，时间范围: {hours:.1f}小时")
            logger.info(f"开始从 Outlook: {email} 检查是否有新的邮件。")
            mail_service = OutlookMailService(user_mail)
            emails = mail_service.fetch_emails(hours=int(hours), skip_processed=True)
            logger.info(f"成功获取 {len(emails)} 封邮件")
            
            # 更新最后检查时间
            monitor_status.last_check_time = now
            monitor_status.last_found_emails = len(emails)
            monitor_status.save()
            
            if not emails:
                logger.info("没有新邮件需要分类")
                return {
                    'status': 'success',
                    'message': '没有新邮件需要分类',
                    'classified_count': 0
                }
            
            # 对邮件进行分类
            method = settings.DEFAULT_EMAIL_CLASSIFICATION_METHOD
            logger.info(f"开始使用 {method} 方法对邮件进行分类")
            results = EmailClassifier.classify_emails(emails, method=method)
            
            # 统计分类结果
            total_classified = 0
            classification_stats = {}
            
            for classification, emails_data in results.items():
                classification_stats[classification] = len(emails_data)
                total_classified += len(emails_data)
                
                # 更新邮件分类
                for data in emails_data:
                    # 获取邮件对象
                    if 'email' in data:
                        email_obj = data['email']
                        email_obj.categories = classification
                        
                        # 保存分类详情
                        email_obj.classification_method = method
                        
                        # 保存置信度（如果有）
                        if 'confidence' in data:
                            email_obj.classification_confidence = data['confidence']
                        
                        # 保存分类理由
                        if 'explanation' in data:
                            email_obj.classification_reason = data['explanation']
                        
                        # 保存匹配规则（如果有）
                        if 'rule_name' in data:
                            email_obj.classification_rule = data['rule_name']
                        
                        # 标记为已处理
                        email_obj.is_processed = True
                        email_obj.processed_time = now
                        
                        # 更新字段列表
                        update_fields = [
                            'categories', 
                            'classification_method', 
                            'classification_confidence', 
                            'classification_reason', 
                            'classification_rule',
                            'is_processed',
                            'processed_time'
                        ]
                        
                        email_obj.save(update_fields=update_fields)
                        logger.debug(f"邮件 '{email_obj.subject[:30]}...' 分类为 '{classification}'，方法: {method}")
                    else:
                        logger.warning(f"邮件数据中缺少 'email' 字段: {data}")
            
            # 更新总分类邮件数
            monitor_status.total_classified_emails += total_classified
            monitor_status.save()
            
            logger.info(f"分类完成，共分类 {total_classified} 封邮件")
            
            # 处理邮件转发
            forwarding_results = []
            if total_classified > 0:
                logger.info("开始处理邮件转发")
                # 创建 Graph API 服务
                from core.services.graph_service import GraphService
                graph_service = GraphService(user_mail)
                # 处理邮件转发
                forwarding_results = EmailForwardingService.process_classified_emails(
                    classification_results=results,
                    mail_service=graph_service
                )
                
                # 标记已转发的邮件
                for result in forwarding_results:
                    if 'message_id' in result:
                        message_id = result['message_id']
                        email_obj = CCEmail.objects.filter(message_id=message_id).first()
                        if email_obj:
                            email_obj.is_forwarded = True
                            email_obj.save(update_fields=['is_forwarded'])
                            logger.debug(f"邮件 '{email_obj.subject[:30]}...' 已标记为已转发")
                
                logger.info(f"邮件转发完成，共转发 {len(forwarding_results)} 封邮件")
            
            return {
                'status': 'success',
                'message': f'成功分类 {total_classified} 封邮件，转发 {len(forwarding_results)} 封邮件',
                'classified_count': total_classified,
                'forwarded_count': len(forwarding_results),
                'classification_stats': classification_stats,
                'forwarding_results': forwarding_results
            }
            
        except Exception as e:
            logger.error(f"检查新邮件失败: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    @classmethod
    def run_monitoring_task(cls):
        """
        运行监控任务，检查所有开启监控的邮箱
        
        此方法应由定时任务调用，如 Celery 任务或 Django 管理命令
        """
        try:
            # 获取所有开启监控的邮箱
            monitor_statuses = CCEmailMonitorStatus.objects.filter(is_monitoring=True)
            logger.info(f"开始运行邮件监控任务，共 {monitor_statuses.count()} 个邮箱需要检查")
            
            for status in monitor_statuses:
                try:
                    logger.info(f"检查邮箱: {status.email}")
                    result = cls.check_new_emails(status.email)
                    logger.info(f"邮箱 {status.email} 检查结果: {result.get('status')}")
                except Exception as e:
                    logger.error(f"检查邮箱 {status.email} 失败: {str(e)}", exc_info=True)
            
            logger.info("邮件监控任务完成")
            
        except Exception as e:
            logger.error(f"运行邮件监控任务失败: {str(e)}", exc_info=True) 