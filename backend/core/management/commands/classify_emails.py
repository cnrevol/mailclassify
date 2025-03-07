from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import CCEmail
from core.services.email_classifier import EmailClassifier
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '对未分类的邮件进行分类'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            help='处理指定小时数内的邮件'
        )

    def handle(self, *args, **options):
        try:
            # 构建查询条件
            query = {}
            if options['hours']:
                time_threshold = timezone.now() - timedelta(hours=options['hours'])
                query['received_time__gte'] = time_threshold

            # 获取未分类的邮件
            emails = list(CCEmail.objects.filter(
                categories='',
                **query
            ).order_by('-received_time'))

            self.stdout.write(f"Found {len(emails)} unclassified emails")

            # 进行分类
            results = EmailClassifier.classify_emails(emails)

            # 输出分类结果
            for classification, emails_data in results.items():
                self.stdout.write(f"\nClassification: {classification}")
                self.stdout.write(f"Found {len(emails_data)} emails")
                
                for data in emails_data:
                    email = data['email']
                    # 更新邮件分类
                    email.categories = classification
                    email.save(update_fields=['categories'])
                    
                    self.stdout.write(
                        f"- {email.subject} ({email.sender})\n"
                        f"  Rule: {data['rule_name']}\n"
                        f"  Reason: {data['explanation']}"
                    )

            self.stdout.write(self.style.SUCCESS('Successfully classified emails'))

        except Exception as e:
            logger.error(f"Error running classification command: {str(e)}")
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}')) 