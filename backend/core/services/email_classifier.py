import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
from ..models import CCEmail, CCEmailClassifyRule
from .ai_classifier import EmailClassificationAgent, ClassifierFactory
from ..utils.email_categories import load_email_categories
import time
from ..sclogging import WebSocketLogger

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

    @classmethod
    def classify_emails(cls, emails: List[CCEmail], method: str = 'stepgo') -> Dict[str, List[Dict[str, Any]]]:
        """
        对邮件进行分类
        
        Args:
            emails: 要分类的邮件列表
            method: 分类方法 ('stepgo', 'single', 'ensemble')
            
        Returns:
            分类结果字典，键为分类名称，值为邮件列表
        """
        if not emails:
            return {}
            
        logger.info(f"开始对 {len(emails)} 封邮件进行分类，使用方法: {method}")
        
        # 重新加载分类类别
        categories = load_email_categories()
        logger.info(f"当前可用的分类类别: {categories}")
        
        # 创建 AI 代理
        agent = EmailClassificationAgent(categories)
        
        # 根据方法设置代理
        if method == 'single':
            # 单模型执行
            model = settings.DEFAULT_AI_MODEL
            logger.info(f"单模型执行，使用模型: {model}")
            agent.setup(model)
        elif method == 'ensemble':
            # 集成执行
            logger.info("集成执行，使用所有可用模型")
            agent.setup()
        else:  # stepgo
            # 步进执行
            logger.info("步进执行，按优先级使用模型")
            agent.setup()
        
        results = {}
        total_emails = len(emails)
        processed_emails = 0
        start_time = time.time()
        
        for email in emails:
            try:
                logger.debug(f"开始处理邮件: {email.subject}...")
                
                # 根据方法进行分类
                if method == 'stepgo':
                    result = cls._stepgo_classify(email, agent)
                elif method == 'single':
                    result = cls._single_classify(email, agent)
                else:  # ensemble
                    result = cls._ensemble_classify(email, agent)
                
                # 处理分类结果
                classification = result.get('classification', 'unclassified')
                if classification not in results:
                    results[classification] = []
                
                results[classification].append({
                    'email': email,
                    'confidence': result.get('confidence', 0.0),
                    'rule_name': result.get('rule_name', 'Default Classification'),
                    'explanation': result.get('explanation', '')
                })
                
                processed_emails += 1
                logger.debug(f"处理进度: {processed_emails}/{total_emails}")
                
            except Exception as e:
                logger.error(f"处理邮件时出错: {str(e)}", exc_info=True)
                if 'error' not in results:
                    results['error'] = []
                results['error'].append({
                    'email': email,
                    'error': str(e)
                })
        
        # 记录分类统计
        elapsed_time = time.time() - start_time
        logger.info(f"分类完成，共处理 {processed_emails}/{total_emails} 封邮件，耗时 {elapsed_time:.2f} 秒")
        
        # 统计各分类的邮件数量
        stats = {k: len(v) for k, v in results.items()}
        logger.info(f"分类结果统计: {', '.join([f'{k}: {v}' for k, v in stats.items()])}")
        
        return results
    
    @classmethod
    def _stepgo_classify(cls, email: CCEmail, agent: EmailClassificationAgent) -> Dict[str, Any]:
        """
        使用步进方法对邮件进行分类
        
        Args:
            email: 要分类的邮件
            agent: AI 代理实例
            
        Returns:
            分类结果
        """
        logger.info(f"开始对邮件 '{email.subject[:50]}...' 进行逐步分类 (stepgo)")
        
        # 第一步：使用决策树进行分类
        logger.info(f"步进分类：第一步 - 对邮件 '{email.subject[:50]}...' 使用决策树进行分类")
        rule_result = cls._apply_rules(email)
        
        if rule_result['classification'] != 'unclassified':
            logger.info(f"步进分类：邮件通过规则成功分类为 '{rule_result['classification']}'")
            return rule_result
        
        # 第二步：使用 FastText 进行分类
        logger.info(f"步进分类：使用 FastText 进行分类 - 邮件 '{email.subject[:50]}...'")
        fasttext_result = cls._single_classify(email, agent, model='fasttext')
        
        if fasttext_result['confidence'] >= settings.FASTTEXT_THRESHOLD:
            logger.info(f"步进分类：FastText 分类结果 '{fasttext_result['classification']}' 置信度 {fasttext_result['confidence']} 达到阈值")
            return fasttext_result
        
        # 第三步：使用 LLM 进行分类
        logger.info(f"步进分类：使用 LLM 进行分类 - 邮件 '{email.subject[:50]}...'")
        llm_result = cls._single_classify(email, agent, model='llm')
        
        if llm_result['confidence'] >= settings.LLM_THRESHOLD:
            logger.info(f"步进分类：邮件通过 LLM 成功分类为 '{llm_result['classification']}'，置信度: {llm_result['confidence']}")
            return llm_result
        
        # 如果所有方法都失败，返回 unclassified
        logger.info(f"步进分类：所有方法都未能成功分类，返回 unclassified")
        return {
            'classification': 'unclassified',
            'confidence': 0.0,
            'rule_name': 'StepGo Classification',
            'explanation': 'All classification methods failed to meet confidence threshold'
        }
    
    @classmethod
    def _single_classify(cls, email: CCEmail, agent: EmailClassificationAgent, model: Optional[str] = None) -> Dict[str, Any]:
        """
        使用单个模型对邮件进行分类
        
        Args:
            email: 要分类的邮件
            agent: AI 代理实例
            model: 要使用的模型名称
            
        Returns:
            分类结果
        """
        # 确保 model 是字符串
        method = model if model is not None else settings.DEFAULT_AI_MODEL
        logger.info(f"使用 {method} 方法对邮件 '{email.subject[:50]}...' 进行分类")
        result = agent.classify_email(email, method=method)
        # 确保 rule_name 是字符串
        if 'rule_name' not in result or result['rule_name'] is None:
            result['rule_name'] = f"{method.upper()} Classification"
        return result
    
    @classmethod
    def _ensemble_classify(cls, email: CCEmail, agent: EmailClassificationAgent) -> Dict[str, Any]:
        """
        使用集成方法对邮件进行分类
        
        Args:
            email: 要分类的邮件
            agent: AI 代理实例
            
        Returns:
            分类结果
        """
        # 获取所有模型的分类结果
        results = []
        for model in settings.AI_MODELS:
            result = cls._single_classify(email, agent, model=model)
            results.append(result)
        
        # 统计各分类的票数
        votes = {}
        for result in results:
            classification = result['classification']
            confidence = result['confidence']
            if classification not in votes:
                votes[classification] = 0
            votes[classification] += confidence
        
        # 选择得票最多的分类
        best_classification = max(votes.items(), key=lambda x: x[1])
        
        return {
            'classification': best_classification[0],
            'confidence': best_classification[1] / len(results),
            'rule_name': 'Ensemble Classification',
            'explanation': f"Ensemble classification using {len(results)} models"
        }
    
    @classmethod
    def _apply_rules(cls, email: CCEmail) -> Dict[str, Any]:
        """
        应用分类规则
        
        Args:
            email: 要分类的邮件
            
        Returns:
            分类结果
        """
        # 获取所有活动规则
        rules = CCEmailClassifyRule.objects.filter(is_active=True).order_by('priority')
        logger.info(f"获取到 {rules.count()} 条活动规则")
        
        # 遍历规则
        for rule in rules:
            logger.debug(f"尝试匹配规则: {rule.name}")
            
            # 检查规则条件
            matches = True
            rule_logs = []
            
            # 检查发件人域名
            if rule.sender_domains:
                has_any_condition = True
                sender_domain = email.sender.split('@')[-1].lower()
                is_domain_match = sender_domain in rule.sender_domains
                rule_logs.append(f"sender_domain: 域名 '{sender_domain}' {'匹配' if is_domain_match else '不匹配'}")
                matches = matches and is_domain_match
            
            # 检查主题关键词
            if rule.subject_keywords:
                has_any_condition = True
                subject_matches = [
                    keyword.lower() for keyword in rule.subject_keywords 
                    if keyword.lower() in email.subject.lower()
                ]
                is_subject_match = len(subject_matches) > 0
                rule_logs.append(f"subject_keywords: {'找到' if is_subject_match else '未找到'}任何主题关键词")
                matches = matches and is_subject_match
            
            # 检查正文关键词
            if rule.body_keywords:
                has_any_condition = True
                body_matches = [
                    keyword.lower() for keyword in rule.body_keywords 
                    if keyword.lower() in email.content.lower()
                ]
                is_body_match = len(body_matches) > 0
                rule_logs.append(f"body_keywords: {'找到' if is_body_match else '未找到'}任何正文关键词")
                matches = matches and is_body_match
            
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
                
                rule_logs.append({
                    'condition': 'attachment_count',
                    'matched': is_count_match,
                    'details': "附件数量符合要求" if is_count_match else ", ".join(count_details)
                })
                matches = matches and is_count_match
            
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
                
                rule_logs.append({
                    'condition': 'attachment_size',
                    'matched': is_size_match,
                    'details': "附件大小符合要求" if is_size_match else ", ".join(size_details)
                })
                matches = matches and is_size_match
            
            # 记录所有匹配结果
            logger.debug(f"规则 '{rule.name}' 匹配结果:")
            for log in rule_logs:
                logger.debug(f"- {log}")
            
            if matches:
                logger.info(f"规则 '{rule.name}' 的所有条件都匹配")
                return {
                    'classification': rule.classification,
                    'confidence': 1.0,
                    'rule_name': rule.name,
                    'explanation': f"Matched rule: {rule.name}"
                }
            else:
                logger.debug(f"规则 '{rule.name}' 的所有条件都不匹配")
        
        # 如果没有匹配的规则，返回 unclassified
        logger.info(f"邮件 '{email.subject[:50]}...' 未匹配任何规则，归类为 'unclassified'")
        return {
            'classification': 'unclassified',
            'confidence': 0.0,
            'rule_name': 'Rule-based Classification',
            'explanation': 'No matching rules found'
        } 