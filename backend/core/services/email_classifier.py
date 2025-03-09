import logging
from typing import List, Dict, Any
from django.conf import settings
from ..models import CCEmail, CCEmailClassifyRule
from .ai_classifier import EmailClassificationAgent, ClassifierFactory
import time

logger = logging.getLogger(__name__)

class EmailClassifier:
    """邮件分类服务"""

    # 分类器工厂实例
    _factory = None
    
    @classmethod
    def get_factory(cls):
        """获取分类器工厂实例"""
        if cls._factory is None:
            cls._factory = ClassifierFactory.get_instance()
        return cls._factory

    @staticmethod
    def classify_emails(emails: List[CCEmail], method: str = "sequence") -> Dict[str, List[Dict[str, Any]]]:
        """
        对邮件列表进行分类
        
        Args:
            emails: 要分类的邮件列表
            method: 分类方法 ('decision_tree', 'llm', 'bert', 'fasttext', 'sequence', 'stepgo')
            
        Returns:
            按分类组织的邮件字典
        """
        result = {}
        
        # 记录开始时间
        start_time = time.time()
        logger.info(f"开始对 {len(emails)} 封邮件进行分类，使用方法: {method}")
        
        # 处理每封邮件
        for email in emails:
            logger.debug(f"开始处理邮件: {email.subject[:50]}...")
            
            try:
                # 根据方法选择分类器
                if method == "decision_tree":
                    classification_result = EmailClassifier._classify_by_decision_tree(email)
                elif method == "sequence":
                    # 先使用决策树进行分类
                    logger.info(f"序列分类：第一步 - 对邮件 '{email.subject[:50]}...' 使用决策树进行分类")
                    classification_result = EmailClassifier._classify_by_decision_tree(email)
                    
                    # 如果邮件未分类，使用 AI 代理进行二次分类
                    if classification_result['classification'] == 'unclassified':
                        logger.info(f"序列分类：邮件 '{email.subject[:50]}...' 未分类，使用 AI 代理进行二次分类")
                        classification_result = EmailClassifier._classify_by_ai_agent(email, 'llm')
                        logger.info("序列分类：完成 AI 代理二次分类")
                    else:
                        logger.info(f"序列分类：邮件已通过决策树成功分类为 '{classification_result['classification']}'")
                elif method == "stepgo":
                    # 逐步尝试不同的分类器，根据置信度阈值判断是否继续
                    logger.info(f"开始对邮件 '{email.subject[:50]}...' 进行逐步分类 (stepgo)")
                    classification_result = EmailClassifier._step_classifier(email)
                    logger.info(f"逐步分类完成，结果: {classification_result['classification']}，置信度: {classification_result.get('confidence', 'N/A')}")
                else:
                    classification_result = EmailClassifier._classify_by_ai_agent(email, method)
                
                # 记录分类结果
                classification = classification_result.get('classification', 'unknown')
                logger.info(f"邮件 '{email.subject[:50]}...' 被 {method} 分类为 '{classification}'")
                
                # 将结果添加到对应分类的列表中
                if classification not in result:
                    result[classification] = []
                
                # 创建邮件结果字典，包含完整的邮件对象
                email_result = {
                    'email': email,  # 包含完整的邮件对象
                    'subject': email.subject,
                    'sender': email.sender,
                    'received_time': email.received_time,
                    'classification': classification,
                    'rule_name': classification_result.get('rule_name', ''),
                    'explanation': classification_result.get('explanation', '')
                }
                
                result[classification].append(email_result)
                
            except Exception as e:
                logger.error(f"处理邮件时出错: {str(e)}", exc_info=True)
                # 将错误邮件归类为 'error'
                if 'error' not in result:
                    result['error'] = []
                    
                # 创建错误结果字典
                error_result = {
                    'email': email,  # 包含完整的邮件对象
                    'subject': email.subject,
                    'sender': email.sender,
                    'received_time': email.received_time,
                    'classification': 'error',
                    'rule_name': '',
                    'explanation': f"Error: {str(e)}"
                }
                    
                result['error'].append(error_result)
        
        # 记录结束时间和统计信息
        end_time = time.time()
        duration = end_time - start_time
        total_emails = len(emails)
        classified_emails = sum(len(emails_list) for emails_list in result.values())
        logger.info(f"分类完成，共处理 {classified_emails}/{total_emails} 封邮件，耗时 {duration:.2f} 秒")
        logger.info(f"分类结果统计: {', '.join([f'{k}: {len(v)}' for k, v in result.items()])}")
        
        return result

    @staticmethod
    def _classify_by_decision_tree(email: CCEmail) -> Dict[str, Any]:
        """使用决策树规则对单个邮件进行分类"""
        try:
            # 获取所有激活的规则
            rules = CCEmailClassifyRule.objects.filter(is_active=True).order_by('priority')
            logger.info(f"获取到 {len(rules)} 条活动规则")

            # 遍历规则进行匹配
            for rule in rules:
                logger.debug(f"尝试匹配规则: {rule.name}")
                if EmailClassifier._match_rule(email, rule):
                    logger.info(f"邮件 '{email.subject[:50]}...' 匹配规则 '{rule.name}'，归类为 '{rule.classification}'")
                    return {
                        'classification': rule.classification,
                        'rule_name': rule.name,
                        'explanation': f"匹配规则: {rule.name}，规则描述: {rule.description}",
                        'confidence': 1.0  # 决策树匹配是确定性的，置信度为 1.0
                    }

            # 如果没有匹配的规则，归类为未分类
            logger.info(f"邮件 '{email.subject[:50]}...' 未匹配任何规则，归类为 'unclassified'")
            return {
                'classification': 'unclassified',
                'rule_name': None,
                'explanation': "未匹配任何规则",
                'confidence': 0.0  # 未匹配任何规则，置信度为 0
            }

        except Exception as e:
            logger.error(f"决策树分类过程中出错: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _classify_by_ai_agent(email: CCEmail, method: str) -> Dict[str, Any]:
        """使用 AI 代理对单个邮件进行分类"""
        try:
            # 获取分类器工厂
            factory = EmailClassifier.get_factory()
            
            # 获取可用的分类
            categories = [rule.classification for rule in CCEmailClassifyRule.objects.filter(is_active=True)]
            if not categories:
                logger.warning("没有可用的分类类别，使用默认类别")
                categories = ["purchase", "techsupport", "festival", "other"]
            
            # 创建分类代理
            agent = EmailClassificationAgent(categories=categories)
            
            # 进行分类
            logger.info(f"使用 {method} 方法对邮件 '{email.subject[:50]}...' 进行分类")
            result = agent.classify_email(email, method=method)
            
            # 确保结果包含置信度和理由
            if 'confidence' not in result:
                result['confidence'] = 0.8  # 默认置信度
            
            if 'explanation' not in result:
                result['explanation'] = f"使用 {method} 方法分类"
                
            logger.info(f"AI 代理将邮件 '{email.subject[:50]}...' 分类为 '{result['classification']}'，置信度: {result.get('confidence', 'N/A')}")
            return result
            
        except Exception as e:
            logger.error(f"AI 代理分类过程中出错: {str(e)}", exc_info=True)
            return {
                'classification': 'error',
                'rule_name': None,
                'explanation': f"分类错误: {str(e)}",
                'confidence': 0.0
            }

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

    @staticmethod
    def _step_classifier(email: CCEmail) -> Dict[str, Any]:
        """
        逐步尝试不同的分类器，直到获得可信的分类结果
        
        Args:
            email: 要分类的邮件
            
        Returns:
            分类结果字典
        """
        try:
            # 1. 首先尝试决策树分类
            logger.info(f"步进分类：第一步 - 对邮件 '{email.subject[:50]}...' 使用决策树进行分类")
            result = EmailClassifier._classify_by_decision_tree(email)
            
            # 如果决策树分类成功（不是 unclassified），直接返回结果
            if result['classification'] != 'unclassified':
                logger.info(f"步进分类：邮件通过决策树成功分类为 '{result['classification']}'")
                return result
            
            # 2. 尝试 FastText 分类
            logger.info(f"步进分类：第二步 - 对邮件 '{email.subject[:50]}...' 使用 FastText 进行分类")
            result = EmailClassifier._classify_by_ai_agent(email, 'fasttext')
            
            # 检查 FastText 分类结果的置信度是否高于阈值
            confidence = result.get('confidence', 0)
            if (result['classification'] != 'unclassified' and 
                result['classification'] != 'error' and 
                confidence >= settings.FASTTEXT_THRESHOLD):
                logger.info(f"步进分类：邮件通过 FastText 成功分类为 '{result['classification']}'，置信度: {confidence}")
                return result
            else:
                logger.info(f"步进分类：FastText 分类结果 '{result['classification']}' 置信度 {confidence} 低于阈值 {settings.FASTTEXT_THRESHOLD}，继续下一步")
            
            # 3. 尝试 BERT 分类
            logger.info(f"步进分类：第三步 - 对邮件 '{email.subject[:50]}...' 使用 BERT 进行分类")
            result = EmailClassifier._classify_by_ai_agent(email, 'bert')
            
            # 检查 BERT 分类结果的置信度是否高于阈值
            confidence = result.get('confidence', 0)
            if (result['classification'] != 'unclassified' and 
                result['classification'] != 'error' and 
                confidence >= settings.BERT_THRESHOLD):
                logger.info(f"步进分类：邮件通过 BERT 成功分类为 '{result['classification']}'，置信度: {confidence}")
                return result
            else:
                logger.info(f"步进分类：BERT 分类结果 '{result['classification']}' 置信度 {confidence} 低于阈值 {settings.BERT_THRESHOLD}，继续下一步")
            
            # 4. 最后尝试 LLM 分类
            logger.info(f"步进分类：第四步 - 对邮件 '{email.subject[:50]}...' 使用 LLM 进行分类")
            result = EmailClassifier._classify_by_ai_agent(email, 'llm')
            
            # 检查 LLM 分类结果的置信度是否高于阈值
            confidence = result.get('confidence', 0)
            if (result['classification'] != 'unclassified' and 
                result['classification'] != 'error' and 
                confidence >= settings.LLM_THRESHOLD):
                logger.info(f"步进分类：邮件通过 LLM 成功分类为 '{result['classification']}'，置信度: {confidence}")
                return result
            else:
                logger.info(f"步进分类：LLM 分类结果 '{result['classification']}' 置信度 {confidence} 低于阈值 {settings.LLM_THRESHOLD}，分类失败")
                # 如果所有方法都未能提供高置信度的分类，返回 unclassified
                return {
                    'classification': 'unclassified',
                    'rule_name': 'Step Classification',
                    'explanation': "所有分类方法都未能提供高置信度的分类结果",
                    'confidence': 0.0
                }
            
        except Exception as e:
            logger.error(f"步进分类过程中出错: {str(e)}", exc_info=True)
            return {
                'classification': 'error',
                'rule_name': 'Step Classification',
                'explanation': f"分类错误: {str(e)}",
                'confidence': 0.0
            } 