from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def load_email_categories():
    """
    从数据库加载邮件分类类别并更新到settings
    """
    try:
        # 延迟导入避免循环依赖
        from ..models import CCEmailClassifyRule
        
        # 获取所有活动的分类规则
        categories = CCEmailClassifyRule.objects.filter(
            is_active=True
        ).values_list('classification', flat=True).distinct()
        
        # 转换为列表并添加默认类别
        categories = list(categories)
        if 'unclassified' not in categories:
            categories.append('unclassified')
            
        # 排序确保结果一致性
        categories.sort()
        
        # 更新settings中的EMAIL_CATEGORIES
        settings.EMAIL_CATEGORIES = categories
        
        logger.info(f"成功加载邮件分类类别: {categories}")
        return categories
    except Exception as e:
        # 如果出错，使用默认类别
        default_categories = ['purchase', 'techsupport', 'festival', 'unclassified']
        settings.EMAIL_CATEGORIES = default_categories
        logger.error(f"加载邮件分类类别失败: {str(e)}, 使用默认类别: {default_categories}")
        return default_categories 