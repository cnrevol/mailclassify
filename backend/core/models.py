from django.db import models
from django.utils.translation import gettext_lazy as _
import logging
from typing import Optional

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

class CCLLMBase(models.Model):
    """LLM基础模型"""
    id: int
    name = models.CharField(max_length=100, verbose_name="名称")
    model_id = models.CharField(max_length=100, verbose_name="模型ID")
    endpoint = models.CharField(max_length=200, verbose_name="API端点")
    api_key = models.CharField(max_length=200, verbose_name="API密钥")
    api_version = models.CharField(max_length=50, verbose_name="API版本")
    temperature = models.FloatField(default=0.7, verbose_name="温度")
    max_tokens = models.IntegerField(default=2000, verbose_name="最大token数")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def chat(self, messages: list, **kwargs) -> Optional[str]:
        """聊天方法"""
        raise NotImplementedError("Subclasses must implement chat method")

    class Meta:
        abstract = True
        verbose_name = "LLM基础模型"
        verbose_name_plural = verbose_name

class CCAzureOpenAI(CCLLMBase):
    """Azure OpenAI模型"""
    deployment_name = models.CharField(max_length=100, verbose_name="部署名称")
    resource_name = models.CharField(max_length=100, verbose_name="资源名称")
    api_version = models.CharField(_('API版本'), max_length=50, default="2023-03-15-preview")

    class Meta:
        db_table = 'cc_azure_openai'
        verbose_name = "Azure OpenAI"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"Azure-{self.name}"

class CCOpenAI(CCLLMBase):
    """OpenAI模型"""
    organization_id = models.CharField(max_length=100, verbose_name="组织ID", null=True, blank=True)

    class Meta:
        verbose_name = "OpenAI"
        verbose_name_plural = verbose_name

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

class CCEmailClassifyRule(CCBaseModel):
    """
    邮件分类规则表
    """
    name = models.CharField(_('规则名称'), max_length=100)
    description = models.TextField(_('规则描述'))
    sender_domains = models.JSONField(_('发件人域名列表'))
    subject_keywords = models.JSONField(_('主题关键词列表'))
    body_keywords = models.JSONField(_('正文关键词列表'))
    min_attachments = models.IntegerField(_('最小附件数'), default=0)
    max_attachments = models.IntegerField(_('最大附件数'), null=True, blank=True)
    min_attachment_size = models.BigIntegerField(_('最小附件大小'), default=0)
    max_attachment_size = models.BigIntegerField(_('最大附件大小'), null=True, blank=True)
    classification = models.CharField(_('分类'), max_length=100)
    priority = models.IntegerField(_('优先级'), default=0)
    is_active = models.BooleanField(_('是否激活'), default=True)

    class Meta:
        db_table = 'cc_emailclassifyrule'
        verbose_name = _('邮件分类规则')
        verbose_name_plural = _('邮件分类规则')
        ordering = ['-priority']

    def __str__(self):
        return f"{self.name} ({self.classification})"

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
    attachment_count = models.IntegerField(_('附件数量'), default=0)
    total_attachment_size = models.BigIntegerField(_('附件总大小(字节)'), default=0)
    attachments_info = models.JSONField(_('附件详细信息'), default=list, blank=True)
    
    # 新增字段
    classification_method = models.CharField(_('分类方法'), max_length=50, blank=True, null=True, 
                                           help_text=_('使用的分类方法，如 decision_tree, llm, bert, fasttext, sequence, stepgo'))
    classification_confidence = models.FloatField(_('分类置信度'), blank=True, null=True,
                                                help_text=_('分类的置信度，范围 0-1'))
    classification_reason = models.TextField(_('分类理由'), blank=True, null=True,
                                           help_text=_('分类的详细理由或依据'))
    classification_rule = models.CharField(_('匹配规则'), max_length=255, blank=True, null=True,
                                         help_text=_('匹配的规则名称'))
    
    # 处理状态标记
    is_processed = models.BooleanField(_('是否已处理'), default=False, 
                                     help_text=_('邮件是否已经被分类处理'))
    is_forwarded = models.BooleanField(_('是否已转发'), default=False,
                                     help_text=_('邮件是否已经被转发'))
    processed_time = models.DateTimeField(_('处理时间'), null=True, blank=True,
                                        help_text=_('邮件被处理的时间'))

    class Meta:
        db_table = 'cc_email'
        verbose_name = _('邮件内容')
        verbose_name_plural = _('邮件内容')
        ordering = ['-received_time']

    def __str__(self):
        return f"{self.subject} ({self.received_time})"

    def update_attachment_info(self, attachments: list) -> None:
        """
        更新附件信息
        
        Args:
            attachments: 附件列表，每个附件应包含 name, size, content_type 等信息
        """
        self.has_attachments = bool(attachments)
        self.attachment_count = len(attachments)
        self.total_attachment_size = sum(a.get('size', 0) for a in attachments)
        self.attachments_info = [
            {
                'name': a.get('name', ''),
                'size': a.get('size', 0),
                'content_type': a.get('contentType', ''),
                'id': a.get('id', '')
            }
            for a in attachments
        ]

class CCForwardingRule(CCBaseModel):
    """
    邮件转发规则表
    """
    name = models.CharField(_('规则名称'), max_length=100)
    rule_type = models.CharField(_('规则类型'), max_length=1)  # 'A'=平均分配, 'B'=直接转发
    email_type = models.CharField(_('邮件类型'), max_length=50)
    description = models.TextField(_('规则描述'))
    forward_message = models.TextField(_('转发消息'))
    priority = models.IntegerField(_('优先级'), default=0)
    is_active = models.BooleanField(_('是否激活'), default=True)

    class Meta:
        db_table = 'cc_forwardingrule'
        verbose_name = _('邮件转发规则')
        verbose_name_plural = _('邮件转发规则')
        ordering = ['-priority']

    def __str__(self):
        return f"{self.name} ({self.email_type})"

class CCForwardingAddress(models.Model):
    """
    邮件转发地址表
    """
    email = models.EmailField(_('邮箱地址'), max_length=254)
    name = models.CharField(_('姓名'), max_length=100)
    is_active = models.BooleanField(_('是否激活'), default=True)
    rule = models.ForeignKey(CCForwardingRule, on_delete=models.CASCADE, related_name='addresses')

    class Meta:
        db_table = 'cc_forwardingaddress'
        verbose_name = _('邮件转发地址')
        verbose_name_plural = _('邮件转发地址')

    def __str__(self):
        return f"{self.name} <{self.email}>"

class CCEmailForwardingLog(CCBaseModel):
    """
    邮件转发日志表
    """
    title = models.CharField(_('邮件标题'), max_length=500)
    sender = models.CharField(_('发件人'), max_length=255)
    received_time = models.DateTimeField(_('接收时间'))
    classification = models.CharField(_('分类'), max_length=100)
    email_type = models.CharField(_('邮件类型'), max_length=50)
    forwarding_recipient = models.TextField(_('转发收件人'))
    message_id = models.CharField(_('邮件ID'), max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'cc_email_forwarding_log'
        verbose_name = _('邮件转发日志')
        verbose_name_plural = _('邮件转发日志')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.classification} - {self.email_type}"

class CCEmailMonitorStatus(models.Model):
    """邮件监控状态"""
    
    email = models.CharField(max_length=255, unique=True, verbose_name="邮箱地址")
    is_monitoring = models.BooleanField(default=False, verbose_name="是否正在监控")
    last_check_time = models.DateTimeField(null=True, blank=True, verbose_name="上次检查时间")
    last_found_emails = models.IntegerField(default=0, verbose_name="上次发现的新邮件数")
    total_classified_emails = models.IntegerField(default=0, verbose_name="总分类邮件数")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 'cc_email_monitor_status'
        verbose_name = "邮件监控状态"
        verbose_name_plural = "邮件监控状态"
        
    def __str__(self):
        return f"{self.email} - {'监控中' if self.is_monitoring else '已停止'}"
