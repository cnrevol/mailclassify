import logging
from django.core.management.base import BaseCommand
from core.services.email_monitor import EmailMonitorService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '运行邮件监控任务，检查并分类新邮件'

    def handle(self, *args, **options):
        try:
            self.stdout.write(self.style.SUCCESS('开始运行邮件监控任务...'))
            EmailMonitorService.run_monitoring_task()
            self.stdout.write(self.style.SUCCESS('邮件监控任务完成'))
        except Exception as e:
            logger.error(f"运行邮件监控任务失败: {str(e)}", exc_info=True)
            self.stdout.write(self.style.ERROR(f'邮件监控任务失败: {str(e)}')) 