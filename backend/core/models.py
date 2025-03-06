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
    """
    email = models.EmailField(_('邮箱地址'), max_length=255, unique=True)
    client_id = models.CharField(_('客户端ID'), max_length=255)
    client_secret = models.CharField(_('客户端密钥'), max_length=255)
    password = models.CharField(_('登录密码'), max_length=255)
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
