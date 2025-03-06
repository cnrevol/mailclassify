from django.db import models
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger('core')

class CCBaseModel(models.Model):
    """
    Base model for all models in the project.
    All tables will have cc_ prefix.
    """
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        abstract = True
        
    def __str__(self):
        return f"{self.__class__.__name__}_{self.pk}"

class CCLLMBase(CCBaseModel):
    """
    LLM基础模型表
    """
    name = models.CharField(_('模型名称'), max_length=100, unique=True)
    model_id = models.CharField(_('模型ID'), max_length=100)
    endpoint = models.URLField(_('API端点'), max_length=255)
    api_key = models.CharField(_('API密钥'), max_length=255)
    api_version = models.CharField(_('API版本'), max_length=50, null=True, blank=True)
    temperature = models.FloatField(_('温度参数'), default=0.7)
    max_tokens = models.IntegerField(_('最大token数'), default=2000)
    is_active = models.BooleanField(_('是否激活'), default=True)
    provider = models.CharField(_('提供商'), max_length=50)
    description = models.TextField(_('描述'), blank=True)

    class Meta:
        abstract = True

class CCAzureOpenAI(CCLLMBase):
    """
    Azure OpenAI模型配置
    """
    deployment_name = models.CharField(_('部署名称'), max_length=100)
    resource_name = models.CharField(_('资源名称'), max_length=100)

    class Meta:
        db_table = 'cc_azure_openai'
        verbose_name = _('Azure OpenAI配置')
        verbose_name_plural = _('Azure OpenAI配置')

    def __str__(self):
        return f"Azure-{self.name}"

class CCOpenAI(CCLLMBase):
    """
    OpenAI模型配置
    """
    organization_id = models.CharField(_('组织ID'), max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'cc_openai'
        verbose_name = _('OpenAI配置')
        verbose_name_plural = _('OpenAI配置')

    def __str__(self):
        return f"OpenAI-{self.name}"

class CCUserMailInfo(CCBaseModel):
    """
    用户邮件信息表
    存储用户的邮件认证信息
    """
    email = models.EmailField(_('邮箱地址'), max_length=255, unique=True)
    client_id = models.CharField(_('Azure客户端ID'), max_length=255)
    client_secret = models.CharField(_('Azure客户端密钥'), max_length=255)
    tenant_id = models.CharField(_('Azure租户ID'), max_length=255, null=True, blank=True)
    access_token = models.TextField(_('访问令牌'), null=True, blank=True)
    refresh_token = models.TextField(_('刷新令牌'), null=True, blank=True)
    token_expires = models.DateTimeField(_('令牌过期时间'), null=True, blank=True)
    last_sync_time = models.DateTimeField(_('最后同步时间'), null=True, blank=True)
    is_active = models.BooleanField(_('是否激活'), default=True)

    class Meta:
        db_table = 'cc_usermail_info'
        verbose_name = _('用户邮件信息')
        verbose_name_plural = _('用户邮件信息')

    def __str__(self):
        return str(self.email)

    def save(self, *args, **kwargs):
        logger.info(f"{'Creating' if not self.pk else 'Updating'} mail info for: {self.email}")
        super().save(*args, **kwargs)

class CCEmail(CCBaseModel):
    """
    邮件内容表
    存储已处理的邮件信息
    """
    user_mail = models.ForeignKey(CCUserMailInfo, on_delete=models.CASCADE, related_name='emails')
    message_id = models.CharField(_('邮件ID'), max_length=255)
    subject = models.CharField(_('邮件主题'), max_length=1000)
    sender = models.EmailField(_('发件人'), max_length=255)
    received_time = models.DateTimeField(_('接收时间'))
    content = models.TextField(_('邮件内容'))
    is_read = models.BooleanField(_('是否已读'), default=False)
    categories = models.CharField(_('邮件分类'), max_length=255, blank=True)
    importance = models.CharField(_('重要性'), max_length=50, default='normal')
    has_attachments = models.BooleanField(_('是否有附件'), default=False)

    class Meta:
        db_table = 'cc_email'
        verbose_name = _('邮件内容')
        verbose_name_plural = _('邮件内容')
        ordering = ['-received_time']

    def __str__(self):
        return f"{self.subject} ({self.received_time})"
