
1. 使用这个路径的python虚拟环境
    C:\worksapce\aifree\ContentsClassification\project\prj1

2. 后端使用python django。

    实现一个python django的后端框架。
    数据库使用postgresql，db链接信息放到.env文件。
    遵守python django编程的最佳实践。
    放到backend路径下。
    生成DB表名用cc_开头。
    使用这个路径的python虚拟环境
    C:\worksapce\aifree\ContentsClassification\project\prj1\venv

3. 前端使用react。

4. 业务描述，后端有如下功能。
    
    创建一个数据库表，表名cc_usermail_info, 包括用户id(存储邮件地址)，邮箱的client_id, cilent_secret, 登录密码。
    同步这个表到数据库。
    开发对应这个表的，增删改查 后端 api 接口,参数你设计。
    

    
    1. 设计实现一个管理LLM实例的工厂方法，
        要求，传入llm名，可以得到这个llm的类对象。
        并且提供，取得llm实例定义信息的方法，为了得到定义信息，初始化某种专用模型对象。
        提供模型执行的接口方法。
        需要支持 azure openai，deepseek，doubao，openai，未来可扩展。
        类对象提供： model_id,endpoint(url),api_key,api_version,temperature,等等）
        模型的链接信息key，url等，定义到.env，通过setting取得。


    后端独立做一个邮件处理的django的服务。要实现一些邮件处理的接口。
    1. 设计实现一个 通过邮件地址，读取outlook邮件接口。

        参数： 邮件地址，邮件个数--读取这个个数的最新邮件，时间（小时）读取这个时间范围内的最新邮件。
        返回值，邮件类对象，包含邮件关键信息，包括但不限于，邮件id,邮件标题，内容，发信地址，收信时间，
    使用azure graph api 读取outlook邮件，认证需要的 azure client id,azure client secret, 从数据库表中取得，表名 cc_user_info, 字段包括userid, client_id, cilent_secret.
    读取过的邮件标记为已读，目的是下次不再重复处理。



实现一个前端react工程，用来调用后端的django接口。
创建到frontend路径下，先实现工程结构。

 需要一个登录页面，
 主页面用onepage页面实现，左侧是可伸缩的菜单



    2.对邮件内容分类的接口
        参数  


后端添加一个服务，提供与前端对话页面交互用。
实现一个接口，在前端对话框提交时调用。
 接口内部实现把前端录入的内容，转发给LLM，使用llm_factory.py,默认使用azure openai,
 这个接口的内部要实现用 ai agent 组织，调用未来后端添加的方法。 这个简单llm调用是暂时测试用。
LLM的返回结果返回给前端，显示到ChatPage.tsx页面上，
前端页面仿照chatgpt的形式显示。
返回的结果可能是文本，表格，表格包含md表格，html表格。图片，要求可以显示这些内容。



在MailConfigPage.tsx 页面操作列后，再添加列，添加按钮，按钮名是  分类开始， 需要有radiobutton的开关效果，点击打开后，按钮名变为分类中。
调用后端 OutlookMailService 类 fetch_emails 方法对应的 api ，views.py 中 OutlookMailView 。 
取得这个邮箱的邮件。 参数默认是2小时以内。
之后，调用 EmailClassifier 的 classify_emails 用 decision_tree 方式对读入的邮件进行分类。
结果保存到ccmail表。

邮件查询页面，录入 







    # OAuth
    path('oauth/authorize', AzureOAuthView.get_auth_url, name='oauth-authorize'),
    path('oauth/callback', AzureOAuthView.handle_callback, name='oauth-callback'),

    


python 代码符合编码规范，最佳实践。
符合面向对象方法，高内聚低耦合。
每个方法最好不超过100行，if分支不超过7层。
python 后端代码，需要日志，必要的处理需要日志。日志用英文。


email_classifier.py 的 classify_emails 方法中再添加一个 method == "stepgo" 的分支，
定义一个step_classifier 的处理。
顺序执行，依次用，决策树分类，fasttext模型分类，bert模型分类，llm模型分类。
当某个分类处理不是other时，返回成功信息，是other时，进入下一级。最后用llm分类。

对于 fasttext模型分类，bert模型分类，llm模型分类，的调用，要从 ai_classifier.py 中提取出通用的处理，和step_classifier 共用。




FASTTEXT_LABEL_MAP = {
    "1": "purchase",
    "2": "techsupport",
    "3": "festival"
}



BERT_LABEL_MAP = {
    1: "purchase",
    2: "techsupport",
    3: "festival"
}




分类完成的邮件，参考表cc_forwardingaddress，cc_forwardingrule 已经定义到了DB.
create table asset.cc_forwardingaddress (
  id bigint not null
  , email character varying(254) not null
  , name character varying(100) not null
  , is_active boolean not null
  , rule_id bigint not null
  , primary key (id)
);


create table asset.cc_forwardingrule (
  id bigint not null
  , name character varying(100) not null
  , rule_type character varying(1) not null
  , email_type character varying(50) not null
  , description text not null
  , forward_message text not null
  , priority integer not null
  , is_active boolean not null
  , created_at timestamp(6) with time zone not null
  , updated_at timestamp(6) with time zone not null
  , primary key (id)
);

做邮件转发处理，
以下这个 邮件分类 与 转发email_type 的对应关系定义在setting文件。
EMAIL_TYPE_MAPPING = {
    'purchase': ['sales_inquiry', 'general_inquiry'],
    'techsupport': ['support_request', 'technical_issue', 'urgent_issue'],
    'Technical support': ['support_request', 'technical_issue', 'urgent_issue'],
}
对照setting.py中定义的这个关系，处理分类：email_type，到表cc_forwardingrule中查找email_type定义的邮件转发定义，
包括，forward_message，name，rule_type，转发邮件地址通过id查找cc_forwardingaddress表的email 地址。

参考以下代码

# 获取对应的email_types
                email_types = settings.EMAIL_TYPE_MAPPING.get(classification.lower(), [])
                logger.debug(f"Mapped email types: {email_types}")
                
                # 对每个email_type进行处理
                for email_type in email_types:
                    logger.info(f"Processing email type: {email_type} for email: {email['subject']}")
                    
                    # 获取转发信息
                    logger.debug("Getting forwarding information")
                    forwarding_info = EmailForwardingService.get_forwarding_info(
                        email_content=email['body_text'],
                        email_type=email_type
                    )
                    
                    if forwarding_info.get('success'):
                        # 转发邮件
                        logger.info(f"Forwarding email to: {forwarding_info['forward_addresses']}")
                        graph_service.forward_email(forwarding_info, email)
                        
                        # 记录到日志
                        logger.debug("Creating log entry in database")
                        log_entry = EmailClassificationLog.objects.create(
                            title=email['subject'],
                            sender=email['from'],
                            received_time=email['received_time'],
                            classification=classification,
                            email_type=email_type,
                            forwarding_recipient=','.join([
                                addr['email'] for addr in forwarding_info['forward_addresses']
                            ]),
                            created_at=timezone.now()
                        )
                        
                        logger.debug(f"Log entry created with ID: {log_entry.id}")
                        processing_results.append({
                            'id': log_entry.id,
                            'title': log_entry.title,
                            'sender': log_entry.sender,
                            'received_time': log_entry.received_time,
                            'classification': log_entry.classification,
                            'email_type': log_entry.email_type,
                            'forwarding_recipient': log_entry.forwarding_recipient,
                            'created_at': log_entry.created_at
                        })
                        logger.info(f"Successfully processed and forwarded email: {email['subject']}")
                    else:
                        logger.warning(f"Failed to get forwarding info for email: {email['subject']}")

class EmailForwardingService:
    @staticmethod
    def get_forwarding_info(email_content: str, email_type: str) -> dict:
        """
        Get forwarding information based on email type and content
        
        Args:
            email_content (str): The content of the email (optional)
            email_type (str): The type of the email
            
        Returns:
            dict: Forwarding information including addresses, message, and priority
        """
        try:
            # Get the active forwarding rule for this email type
            rule = ForwardingRule.objects.filter(
                email_type=email_type,
                is_active=True
            ).prefetch_related('addresses').first()
            
            if not rule:
                return {
                    'success': False,
                    'error': f'No active forwarding rule found for email type: {email_type}'
                }
            
            # Get active forwarding addresses
            addresses = rule.addresses.filter(is_active=True)
            if not addresses.exists():
                return {
                    'success': False,
                    'error': f'No active forwarding addresses found for rule: {rule.name}'
                }
            
            # If rule type is 'A' (Average Distribution), get the optimal address
            if rule.rule_type == 'A':
                address = TaskAssignmentService.get_optimal_address(
                    addresses=addresses,
                    task_type=email_type
                )
                forward_addresses = [{'email': address.email, 'name': address.name}]
            else:  # For rule type 'B' (Direct Forward)
                forward_addresses = [
                    {'email': addr.email, 'name': addr.name}
                    for addr in addresses
                ]
            
            return {
                'success': True,
                'rule_type': rule.rule_type,
                'forward_addresses': forward_addresses,
                'forward_message': rule.forward_message,
                'priority': rule.priority,
                'rule_name': rule.name
            }
            
        except Exception as e:
            logger.error(f"Error getting forwarding info: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Error processing forwarding request: {str(e)}'
            }



在 cc_email 表中添加字段，保存分类信息，包括使用的分类方式，置信度，理由。在分类处理结束时，保存这些内容。

email_classifier.py classify_emails 处理中 ,fasttext,bert 模型的判断结果的置信度 confidence 做判定，当高于设定的阈值时，认为分类成功，否则，进入下一级处理。
阈值在setting.py中配置。分别是，FASTTEXT_THRESHOLD = 0.95
BERT_THRESHOLD = 0.8

对 email_classifier.py 的 _step_classifier 中，fasttext 和bert模型的分类判定，
我要通过外部配置，可以实现 1. 两种模型都做分类执行，对分类结果都做判定，同时大于阈值，才算分类成功。2.只执行其中一种模型。3，还是顺序执行，可以指定fasttext,bert的先后。
请设计一个配置方法，并在 _step_classifier 中实现。