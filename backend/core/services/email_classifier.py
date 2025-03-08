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
            logger.info(f"开始邮件分类，共 {len(emails)} 封邮件，使用方法: {method}")
            
            if method == "decision_tree":
                results = EmailClassifier._classify_by_decision_tree(emails)
            else:
                results = EmailClassifier._classify_by_ai_agent(emails, method)
                
            # 记录分类结果统计
            for category, items in results.items():
                logger.info(f"分类 '{category}': {len(items)} 封邮件")
                
            return results
        except Exception as e:
            logger.error(f"邮件分类过程中出错: {str(e)}", exc_info=True)
            return {"error": [{"email": None, "rule_name": None, "explanation": str(e)}]}

    @staticmethod
    def _classify_by_decision_tree(emails: List[CCEmail]) -> Dict[str, List[Dict[str, Any]]]:
        """使用决策树规则进行分类"""
        try:
            # 获取所有激活的规则
            rules = CCEmailClassifyRule.objects.filter(is_active=True).order_by('priority')
            logger.info(f"获取到 {len(rules)} 条活动规则")
            results = {}

            for email in emails:
                logger.debug(f"开始处理邮件: {email.subject[:50]}...")
                classified = False
                
                # 遍历规则进行匹配
                for rule in rules:
                    logger.debug(f"尝试匹配规则: {rule.name}")
                    if EmailClassifier._match_rule(email, rule):
                        # 添加到分类结果
                        if rule.classification not in results:
                            results[rule.classification] = []
                            
                        results[rule.classification].append({
                            'email': email,
                            'rule_name': rule.name,
                            'explanation': f"Matched rule: {rule.name}"
                        })
                        logger.info(f"邮件 '{email.subject[:50]}...' 匹配规则 '{rule.name}'，归类为 '{rule.classification}'")
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
                    logger.info(f"邮件 '{email.subject[:50]}...' 未匹配任何规则，归类为 'unclassified'")

            return results

        except Exception as e:
            logger.error(f"决策树分类过程中出错: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _classify_by_ai_agent(emails: List[CCEmail], method: str) -> Dict[str, List[Dict[str, Any]]]:
        """使用AI代理进行分类"""
        try:
            # 获取可用的分类类别
            categories = list(CCEmailClassifyRule.objects.values_list(
                'classification', flat=True).distinct())
            if not categories:
                logger.error("没有找到可用的分类类别")
                raise ValueError("No classification categories available")

            logger.info(f"使用 {method} 方法进行分类，可用类别: {categories}")

            # 初始化分类代理
            agent = EmailClassificationAgent(categories)
            agent.setup()  # 使用默认配置
            logger.info(f"AI 分类代理初始化完成")

            results = {}
            for email in emails:
                logger.debug(f"开始处理邮件: {email.subject[:50]}...")
                
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
                
                logger.info(f"邮件 '{email.subject[:50]}...' 被 {method} 分类为 '{classification}'")

            return results

        except Exception as e:
            logger.error(f"AI 代理分类过程中出错: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _match_rule(email: CCEmail, rule: CCEmailClassifyRule) -> bool:
        """检查邮件是否匹配规则"""
        try:
            match_results = []
            has_any_condition = False  # 标记是否有任何条件被设置
            
            # 检查发件人域名
            if rule.sender_domains:
                has_any_condition = True
                sender_domain = email.sender.split('@')[-1].lower()
                is_domain_match = sender_domain in rule.sender_domains
                match_results.append({
                    'condition': 'sender_domain',
                    'matched': is_domain_match,
                    'details': f"域名 '{sender_domain}' {'匹配' if is_domain_match else '不匹配'}"
                })
                if is_domain_match:
                    logger.info(f"规则 '{rule.name}' 的发件人域名条件匹配成功")
                    return True

            # 检查主题关键词
            if rule.subject_keywords:
                has_any_condition = True
                subject_matches = [
                    keyword.lower() for keyword in rule.subject_keywords 
                    if keyword.lower() in email.subject.lower()
                ]
                is_subject_match = len(subject_matches) > 0
                match_results.append({
                    'condition': 'subject_keywords',
                    'matched': is_subject_match,
                    'details': f"找到关键词: {subject_matches}" if is_subject_match else "未找到任何主题关键词"
                })
                if is_subject_match:
                    logger.info(f"规则 '{rule.name}' 的主题关键词条件匹配成功: {subject_matches}")
                    return True

            # 检查正文关键词
            if rule.body_keywords:
                has_any_condition = True
                body_matches = [
                    keyword.lower() for keyword in rule.body_keywords 
                    if keyword.lower() in email.content.lower()
                ]
                is_body_match = len(body_matches) > 0
                match_results.append({
                    'condition': 'body_keywords',
                    'matched': is_body_match,
                    'details': f"找到关键词: {body_matches}" if is_body_match else "未找到任何正文关键词"
                })
                if is_body_match:
                    logger.info(f"规则 '{rule.name}' 的正文关键词条件匹配成功: {body_matches}")
                    return True

            # 检查附件数量
            if rule.min_attachments > 0 or rule.max_attachments:
                has_any_condition = True
                is_count_match = True
                count_details = []
                
                if email.attachment_count < rule.min_attachments:
                    is_count_match = False
                    count_details.append(f"数量({email.attachment_count})小于最小要求({rule.min_attachments})")
                
                if rule.max_attachments and email.attachment_count > rule.max_attachments:
                    is_count_match = False
                    count_details.append(f"数量({email.attachment_count})超过最大限制({rule.max_attachments})")
                
                match_results.append({
                    'condition': 'attachment_count',
                    'matched': is_count_match,
                    'details': "附件数量符合要求" if is_count_match else ", ".join(count_details)
                })
                if is_count_match:
                    logger.info(f"规则 '{rule.name}' 的附件数量条件匹配成功")
                    return True

            # 检查附件大小
            if rule.min_attachment_size > 0 or rule.max_attachment_size:
                has_any_condition = True
                is_size_match = True
                size_details = []
                
                if email.total_attachment_size < rule.min_attachment_size:
                    is_size_match = False
                    size_details.append(f"大小({email.total_attachment_size}B)小于最小要求({rule.min_attachment_size}B)")
                
                if rule.max_attachment_size and email.total_attachment_size > rule.max_attachment_size:
                    is_size_match = False
                    size_details.append(f"大小({email.total_attachment_size}B)超过最大限制({rule.max_attachment_size}B)")
                
                match_results.append({
                    'condition': 'attachment_size',
                    'matched': is_size_match,
                    'details': "附件大小符合要求" if is_size_match else ", ".join(size_details)
                })
                if is_size_match:
                    logger.info(f"规则 '{rule.name}' 的附件大小条件匹配成功")
                    return True

            # 记录所有匹配结果
            logger.debug(f"规则 '{rule.name}' 匹配结果:")
            for result in match_results:
                logger.debug(f"- {result['condition']}: {result['details']}")

            # 如果规则没有设置任何条件，返回 False
            if not has_any_condition:
                logger.warning(f"规则 '{rule.name}' 未设置任何条件")
                return False

            # 如果所有条件都检查完还没有返回 True，说明没有任何条件匹配
            logger.debug(f"规则 '{rule.name}' 的所有条件都不匹配")
            return False

        except Exception as e:
            logger.error(f"匹配规则 '{rule.name}' 时出错: {str(e)}", exc_info=True)
            return False 