from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import logging
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from core.models import CCEmail
from core.services.email_classifier import EmailClassifier

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '对未分类的邮件进行分类'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            help='处理指定小时数内的邮件'
        )
        parser.add_argument(
            '--method',
            type=str,
            choices=['decision_tree', 'llm', 'bert', 'fasttext'],
            default='decision_tree',
            help='分类方法: decision_tree, llm, bert, fasttext'
        )

    def handle(self, *args, **options):
        try:
            logger.info("Starting email classification command")
            logger.info(f"Classification method: {options['method']}")
            
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
                        email.save(update_fields=['categories'])
                        logger.debug(f"Successfully updated email {email.id} category to '{classification}'")
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

        except Exception as e:
            logger.error("Error running classification command", exc_info=True)
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            ) 