from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import logging
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from core.models import CCEmail, CCUserMailInfo
from core.services.email_classifier import EmailClassifier

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '对未分类的邮件进行分类'

    def add_arguments(self, parser):
        parser.add_argument(
            '--method',
            type=str,
            default='stepgo',
            help='分类方法 (decision_tree, llm, bert, fasttext, sequence, stepgo)'
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=None,
            help='处理指定小时数内的邮件'
        )
        parser.add_argument(
            '--enable-forwarding',
            action='store_true',
            default=True,
            help='启用邮件转发功能'
        )
        parser.add_argument(
            '--disable-forwarding',
            action='store_false',
            dest='enable_forwarding',
            help='禁用邮件转发功能'
        )

    def handle(self, *args, **options):
        try:
            logger.info("Starting email classification command")
            logger.info(f"Classification method: {options['method']}")
            logger.info(f"Enable forwarding: {options['enable_forwarding']}")
            
            # 构建查询条件
            query = {}
            if options['hours']:
                time_threshold = timezone.now() - timedelta(hours=options['hours'])
                query['received_time__gte'] = time_threshold
                logger.info(f"Processing emails from the last {options['hours']} hours")

            # 获取未分类的邮件
            emails = list(CCEmail.objects.filter(
                categories='',
                **query
            ).order_by('-received_time'))

            logger.info(f"Found {len(emails)} unclassified emails")
            
            if not emails:
                logger.info("No emails to classify")
                self.stdout.write("No emails to classify")
                return

            # 进行分类
            logger.debug("Starting classification process")
            results = EmailClassifier.classify_emails(emails, method=options['method'])

            # 输出分类结果
            total_processed = 0
            for classification, emails_data in results.items():
                logger.info(f"Classification '{classification}': {len(emails_data)} emails")
                total_processed += len(emails_data)
                
                for data in emails_data:
                    email = data['email']
                    logger.debug(
                        f"Classifying email: ID={email.id}, "
                        f"Subject='{email.subject}', "
                        f"Sender='{email.sender}'"
                    )
                    
                    # 更新邮件分类
                    try:
                        email.categories = classification
                        
                        # 保存分类详情
                        email.classification_method = options['method']
                        
                        # 保存置信度（如果有）
                        if 'confidence' in data:
                            email.classification_confidence = data['confidence']
                        
                        # 保存分类理由
                        if 'explanation' in data:
                            email.classification_reason = data['explanation']
                        
                        # 保存匹配规则（如果有）
                        if 'rule_name' in data:
                            email.classification_rule = data['rule_name']
                        
                        # 更新字段列表
                        update_fields = [
                            'categories', 
                            'classification_method', 
                            'classification_confidence', 
                            'classification_reason', 
                            'classification_rule'
                        ]
                        
                        email.save(update_fields=update_fields)
                        logger.debug(f"Successfully updated email {email.id} category to '{classification}' with method '{options['method']}'")
                    except Exception as e:
                        logger.error(f"Failed to update email {email.id} category: {str(e)}")
                        continue
                    
                    self.stdout.write(
                        f"- {email.subject} ({email.sender})\n"
                        f"  Method: {options['method']}\n"
                        f"  Rule/Model: {data['rule_name']}\n"
                        f"  Reason: {data['explanation']}"
                    )

            logger.info(f"Classification completed. Total processed: {total_processed} emails")
            self.stdout.write(self.style.SUCCESS(f'Successfully classified {total_processed} emails'))
            
            # 处理邮件转发
            if options['enable_forwarding'] and total_processed > 0:
                logger.info("Starting email forwarding process")
                self.stdout.write("Starting email forwarding process...")
                
                # 获取所有邮件的用户邮箱配置
                user_mail_ids = set(email.user_mail.id for email in emails)
                user_mails = {
                    um.id: um for um in CCUserMailInfo.objects.filter(id__in=user_mail_ids)
                }
                
                # 按用户邮箱分组处理
                forwarded_count = 0
                for user_mail_id, user_mail in user_mails.items():
                    # 过滤出当前用户的邮件
                    user_results = {}
                    for classification, emails_data in results.items():
                        user_emails_data = [
                            data for data in emails_data 
                            if data['email'].user_mail.id == user_mail_id
                        ]
                        if user_emails_data:
                            user_results[classification] = user_emails_data
                    
                    if not user_results:
                        continue
                    
                    # 创建 Graph API 服务
                    from core.services.graph_service import GraphService
                    graph_service = GraphService(user_mail)
                    
                    # 处理邮件转发
                    from core.services.email_forwarding import EmailForwardingService
                    forwarding_results = EmailForwardingService.process_classified_emails(
                        classification_results=user_results,
                        graph_service=graph_service
                    )
                    
                    forwarded_count += len(forwarding_results)
                    
                    # 输出转发结果
                    for result in forwarding_results:
                        self.stdout.write(
                            f"- Forwarded: {result['title']}\n"
                            f"  Classification: {result['classification']}\n"
                            f"  Email Type: {result['email_type']}\n"
                            f"  Recipients: {result['forwarding_recipient']}"
                        )
                
                logger.info(f"Forwarding completed. Total forwarded: {forwarded_count} emails")
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully forwarded {forwarded_count} emails')
                )

        except Exception as e:
            logger.error("Error running classification command", exc_info=True)
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            ) 