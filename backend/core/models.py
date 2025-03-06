from django.db import models
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger('core')

class CCBaseModel(models.Model):
    """
    Base model for all models in the project.
    All tables will have cc_ prefix.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        
    def __str__(self):
        return f"{self.__class__.__name__}_{self.id}"

# Example model using the base class:
class CCExample(CCBaseModel):
    """
    Example model showing how to use the base model.
    Table name will be cc_example
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'cc_example'  # Enforcing cc_ prefix

class CCUserMailInfo(models.Model):
    """
    用户邮件信息表
    """
    email = models.EmailField(_('邮箱地址'), max_length=255, unique=True)
    client_id = models.CharField(_('客户端ID'), max_length=255)
    client_secret = models.CharField(_('客户端密钥'), max_length=255)
    password = models.CharField(_('登录密码'), max_length=255)
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)
    is_active = models.BooleanField(_('是否激活'), default=True)

    class Meta:
        db_table = 'cc_usermail_info'
        verbose_name = _('用户邮件信息')
        verbose_name_plural = _('用户邮件信息')

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        logger.info(f"{'Creating' if not self.pk else 'Updating'} mail info for: {self.email}")
        super().save(*args, **kwargs)
