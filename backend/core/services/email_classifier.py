import logging
from typing import Dict, Any, Optional, List
from ..models import CCEmail, CCEmailClassifyRule

logger = logging.getLogger(__name__)

class EmailClassifier:
    """邮件分类服务"""

    @staticmethod
    def classify_email(email: CCEmail) -> Optional[Dict[str, Any]]:
        """
        对单个邮件进行分类
        
        Args:
            email: CCEmail实例
            
        Returns:
            分类结果字典，包含以下字段：
            - classification: 分类名称
            - confidence: 置信度
            - method: 分类方法
            - rule_name: 匹配的规则名称
            - explanation: 匹配原因说明
        """
        try:
            rules = CCEmailClassifyRule.objects.filter(is_active=True).order_by('-priority')
            logger.info(f"Found {rules.count()} active rules")
            
            for rule in rules:
                matched_reasons = []
                
                # 检查发件人域名
                if rule.sender_domains:
                    if '@' in email.sender:
                        sender_domain = email.sender.split('@')[1].lower()
                        if sender_domain in rule.sender_domains:
                            logger.debug(f"Rule {rule.name}: Sender domain {sender_domain} matched")
                            matched_reasons.append(f'Sender domain {sender_domain} matched')
                
                # 检查主题关键词
                if rule.subject_keywords:
                    subject = email.subject.lower()
                    matched_keywords = [kw for kw in rule.subject_keywords if kw.lower() in subject]
                    if matched_keywords:
                        logger.debug(f"Rule {rule.name}: Subject keywords matched: {matched_keywords}")
                        matched_reasons.append(f'Subject contains keywords: {matched_keywords}')
                
                # 检查正文关键词
                if rule.body_keywords:
                    body = email.content.lower()
                    matched_keywords = [kw for kw in rule.body_keywords if kw.lower() in body]
                    if matched_keywords:
                        logger.debug(f"Rule {rule.name}: Body keywords matched: {matched_keywords}")
                        matched_reasons.append(f'Body contains keywords: {matched_keywords}')
                
                # 检查附件数量
                if rule.min_attachments > 0 or rule.max_attachments:
                    if email.attachment_count >= rule.min_attachments:
                        matched_reasons.append(f'Attachment count ({email.attachment_count}) >= {rule.min_attachments}')
                    if rule.max_attachments and email.attachment_count <= rule.max_attachments:
                        matched_reasons.append(f'Attachment count ({email.attachment_count}) <= {rule.max_attachments}')
                
                # 检查附件大小
                if rule.min_attachment_size > 0 or rule.max_attachment_size:
                    if email.total_attachment_size >= rule.min_attachment_size:
                        matched_reasons.append(
                            f'Total attachment size ({email.total_attachment_size} bytes) >= {rule.min_attachment_size}'
                        )
                    if rule.max_attachment_size and email.total_attachment_size <= rule.max_attachment_size:
                        matched_reasons.append(
                            f'Total attachment size ({email.total_attachment_size} bytes) <= {rule.max_attachment_size}'
                        )
                
                # 如果有任何条件匹配
                if matched_reasons:
                    logger.info(f"Rule {rule.name} matched: {matched_reasons}")
                    return {
                        'classification': rule.classification,
                        'confidence': 1.0,
                        'method': 'Rule Based',
                        'rule_name': rule.name,
                        'explanation': ', '.join(matched_reasons)
                    }
                else:
                    logger.debug(f"Rule {rule.name} did not match any conditions")
            
            logger.info("No rules matched")
            return None
            
        except Exception as e:
            logger.error(f"Error classifying email: {str(e)}")
            return None

    @staticmethod
    def classify_emails(emails: List[CCEmail]) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量对邮件进行分类
        
        Args:
            emails: CCEmail实例列表
            
        Returns:
            分类结果字典，key为分类名称，value为该分类下的邮件列表
        """
        try:
            results = {}
            for email in emails:
                result = EmailClassifier.classify_email(email)
                if result:
                    classification = result['classification']
                    if classification not in results:
                        results[classification] = []
                    results[classification].append({
                        'email': email,
                        'rule_name': result['rule_name'],
                        'explanation': result['explanation']
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error classifying emails: {str(e)}")
            return {} 