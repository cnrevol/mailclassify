from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        """
        在应用程序准备就绪时执行初始化操作
        """
        # 使用延迟导入避免循环依赖
        from .utils.email_categories import load_email_categories
        load_email_categories()
