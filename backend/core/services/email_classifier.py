import logging
from typing import List, Dict, Any
from django.conf import settings
from ..models import CCEmail, CCEmailClassifyRule
from .ai_classifier import EmailClassificationAgent

logger = logging.getLogger(__name__)

class EmailClassifier:
    """邮件分类服务"""

    @staticmethod
    def classify_emails(emails: List[CCEmail], method: str = "decision_tree") -> Dict[str, List[Dict[str, Any]]]:
        """
        对邮件进行分类
        
        Args:
            emails: 待分类的邮件列表
            method: 分类方法 ('decision_tree', 'llm', 'bert', 'fasttext')
            
        Returns:
            分类结果字典，key为分类名称，value为该分类下的邮件列表
        """
        try:
            if method == "decision_tree":
                return EmailClassifier._classify_by_decision_tree(emails)
            else:
                return EmailClassifier._classify_by_ai_agent(emails, method)
        except Exception as e:
            logger.error(f"Error classifying emails: {str(e)}")
            return {"error": [{"email": None, "rule_name": None, "explanation": str(e)}]}

    @staticmethod
    def _classify_by_decision_tree(emails: List[CCEmail]) -> Dict[str, List[Dict[str, Any]]]:
        """使用决策树规则进行分类"""
        try:
            # 获取所有激活的规则
            rules = CCEmailClassifyRule.objects.filter(is_active=True).order_by('-priority')
            results = {}

            for email in emails:
                classified = False
                
                # 遍历规则进行匹配
                for rule in rules:
                    if EmailClassifier._match_rule(email, rule):
                        # 添加到分类结果
                        if rule.classification not in results:
                            results[rule.classification] = []
                            
                        results[rule.classification].append({
                            'email': email,
                            'rule_name': rule.name,
                            'explanation': f"Matched rule: {rule.name}"
                        })
                        classified = True
                        break
                
                # 如果没有匹配的规则，归类为未分类
                if not classified:
                    if 'unclassified' not in results:
                        results['unclassified'] = []
                    results['unclassified'].append({
                        'email': email,
                        'rule_name': None,
                        'explanation': "No matching rules found"
                    })

            return results

        except Exception as e:
            logger.error(f"Error in decision tree classification: {str(e)}")
            raise

    @staticmethod
    def _classify_by_ai_agent(emails: List[CCEmail], method: str) -> Dict[str, List[Dict[str, Any]]]:
        """使用AI代理进行分类"""
        try:
            # 获取可用的分类类别
            categories = list(CCEmailClassifyRule.objects.values_list(
                'classification', flat=True).distinct())
            if not categories:
                raise ValueError("No classification categories available")

            # 初始化分类代理
            agent = EmailClassificationAgent(categories)
            agent.setup()  # 使用默认配置

            results = {}
            for email in emails:
                # 使用指定方法进行分类
                result = agent.classify_email(email, method)
                
                # 获取分类结果
                classification = result.get('classification', 'unknown')
                if classification not in results:
                    results[classification] = []
                
                results[classification].append({
                    'email': email,
                    'rule_name': f"{method.upper()} Classification",
                    'explanation': result.get('explanation', 'No explanation provided')
                })

            return results

        except Exception as e:
            logger.error(f"Error in AI agent classification: {str(e)}")
            raise

    @staticmethod
    def _match_rule(email: CCEmail, rule: CCEmailClassifyRule) -> bool:
        """检查邮件是否匹配规则"""
        try:
            # 检查发件人域名
            sender_domain = email.sender.split('@')[-1].lower()
            if rule.sender_domains and sender_domain not in rule.sender_domains:
                return False

            # 检查主题关键词
            if rule.subject_keywords and not any(
                keyword.lower() in email.subject.lower() 
                for keyword in rule.subject_keywords
            ):
                return False

            # 检查正文关键词
            if rule.body_keywords and not any(
                keyword.lower() in email.content.lower() 
                for keyword in rule.body_keywords
            ):
                return False

            # 检查附件数量
            if email.attachment_count < rule.min_attachments:
                return False
            if rule.max_attachments and email.attachment_count > rule.max_attachments:
                return False

            # 检查附件大小
            if email.total_attachment_size < rule.min_attachment_size:
                return False
            if rule.max_attachment_size and email.total_attachment_size > rule.max_attachment_size:
                return False

            return True

        except Exception as e:
            logger.error(f"Error matching rule: {str(e)}")
            return False 