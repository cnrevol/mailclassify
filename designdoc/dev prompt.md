
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



前端 MailConfigPage.tsx 页面的handleClassify 方法，在点击按钮后被触发执行，调用后端 views.py ClassifyEmailsView 进行处理。
现在的流程是，点击按钮后，触发一次，但是按钮上的文字显示 分类中，我要对邮箱监控，发现有新邮件后，就读取新邮件，进行分类处理。请帮我设计一下，如何进行监控邮件，
是在前端不断提交请求，还是后端启动线程，怎样的解决方案比较好。要保证前端知道在监控中的状态，可以通过点击 分类中 按钮，停止监控。


mail_service.py 的 fetch_emails 方法中，对已经读取分类过的邮件，可以进行识别吗？我要只读取没有处理过的邮件。
需要在views.py 的 ClassifyEmailsView 中对转发过的邮件做标识处理吗？


前端需要修改，
在 MailConfigPage.tsx 页面点击监控按钮后，弹出一个窗口，页面设计如图。
窗口宽度可以调节，默认宽度暂定1024px。
窗口页面显示当前正在监控的信息，包括，读入邮件总数，正在分类处理的邮件数，已经处理完成的邮件数。
每个分类结果件数。
监控师的意思是读取邮件处理的拟人化名称，后边显示读入邮件的进度，用进度条+百分比表示。
处理智能体 是对分析邮件处理的高逼格名称，后边显示处理进度。用进度条+百分比表示。
窗口下部一部分区域显示处理日志，使用现在输出到applog的内容就可以。

后端需要修改的内容，
    1. 监控触发，前后端通信改为websocket长连接。
    2. 后端的邮件监控，改为前端触发websocket,后端启动进程，间隔10（setting.py设定）秒，检查扫描邮箱，读取邮件。
    3. 封装一下 logging 类，把日志输出，websocket发送日志到前端封装到一起，把logger输出的内容，输出到前端。这样现在输出日志的代码可以不需要修改。
    4. 统计读入邮件总件数，正在分类处理的邮件数，已经处理完成的邮件数。每个分类结果件数。也发送到前端显示。



-----



在 ​Order to Cash（O2C）​ 流程中，子流程的英文表达及对应环节如下：

1. ​Order Entry & Validation​（订单录入与验证）
包括接收客户订单、验证订单细节（如产品库存、价格、付款条件）以及确认订单可执行性。此阶段需确保订单数据准确，并可能涉及信用检查。

2. ​Order Fulfillment & Shipping​（订单履行与发货）
涵盖拣货、包装、物流安排及实际发货。例如，Oracle系统中的 ​Order-to-Shipment 子流程包含库存保留、拣料核发和出货确认。

3. ​Invoicing/Billing​（发票开具）
生成并发送发票给客户，包含商品明细、税金计算和付款条款。ERP系统中可能称为 ​Customer Invoice to Cash，需与订单数据和会计科目联动。

4. ​Accounts Receivable Management​（应收账款管理）
跟踪发票状态、管理应收账款到期日，并处理客户付款。例如，Oracle通过 ​AutoAccounting 机制整合交易类型、客户信息以生成准确会计科目。

5. ​Cash Application & Reconciliation​（现金应用与对账）
将客户付款与应收账款匹配，并完成对账。涉及 ​Cash Application 子流程，需处理全额/部分付款或扣款（Deductions）。

6. ​Collections & Deductions Management​（催收与扣款管理）
对逾期未付款项进行催收，并处理客户扣款争议。例如，Oracle通过 ​Customer Statement to Collections 机制提醒客户付款并管理贷项余额。

我要进行如下分类识别，
​1. 对于，Order Entry & Validation​（订单录入与验证）和 ​Order Fulfillment & Shipping​（订单履行与发货） 业务的相关邮件，需要被识别为Order相关任务。
2. 对于，Invoicing/Billing​（发票开具） 相关业务的邮件，需要被识别为Billing相关业务。
3. 对于，Accounts Receivable Management​（应收账款管理），Cash Application & Reconciliation​（现金应用与对账）业务的相关邮件，需要被识别成Cash业务。
4. 对于，​Collections & Deductions Management​（催收与扣款管理）业务的相关邮件，需要被识别成Collections业务。

我要用LLM对这些业务的邮件内容进行识别，分类，请你给我整理出对以上四个分类的描述提示词，我可以用这个提示词发送给llm，llm根据这个提示词，可以识别出邮件属于哪个分类。

另外，我还要对所有邮件内容的情感进行识别，如果邮件中有抱怨的情绪，如果邮件中有愤怒的情绪，那么要给存在这类情绪的邮件分类，请你对抱怨情绪，愤怒情绪进行提示词描述。

如果邮件中有技术咨询，技术相关的问题，那么要分类为技术支持。请展开对技术支持做提示词描述。

---


以下是针对邮件分类的提示词描述，可用于 LLM 进行邮件分类：  

---

### **业务分类提示词**  

#### **1. Order（订单相关）**  
**描述**：  
请分析以下邮件内容，判断是否与订单处理相关。如果邮件涉及订单录入、订单验证、库存检查、价格确认、信用检查、订单执行、订单拣选、物流安排、出货确认等内容，请将其分类为 "Order"。  

**关键词**（可作为辅助）：  
订单录入、订单验证、库存检查、价格确认、付款条件、信用检查、拣选、包装、物流安排、发货、库存保留、出货确认。  

---

#### **2. Billing（发票相关）**  
**描述**：  
请分析以下邮件内容，判断是否与发票开具相关。如果邮件涉及发票生成、发票发送、商品明细、税金计算、付款条款、账务联动等内容，请将其分类为 "Billing"。  

**关键词**（可作为辅助）：  
发票、账单、应收发票、税金计算、付款条款、客户账单、财务凭证、账务调整。  

---

#### **3. Cash（应收账款 & 现金对账相关）**  
**描述**：  
请分析以下邮件内容，判断是否与应收账款或现金对账相关。如果邮件涉及发票跟踪、应收账款到期管理、客户付款匹配、部分付款、扣款处理、财务对账等内容，请将其分类为 "Cash"。  

**关键词**（可作为辅助）：  
应收账款、发票状态、到期日、付款匹配、部分付款、全额付款、扣款、财务对账、收款核销。  

---

#### **4. Collections（催收 & 扣款管理相关）**  
**描述**：  
请分析以下邮件内容，判断是否与催收或扣款管理相关。如果邮件涉及逾期未付款的催收、客户扣款争议、付款提醒、信用额度管理、贷项余额调整等内容，请将其分类为 "Collections"。  

**关键词**（可作为辅助）：  
催收、逾期账款、付款提醒、扣款争议、贷项余额、信用额度、未支付发票、客户催款、违约金。  

---

### **情感分类提示词**  

#### **5. 抱怨（Complaint）**  
**描述**：  
请分析以下邮件内容，判断是否包含客户的抱怨或不满情绪。如果邮件中提到服务质量问题、交付延误、错误账单、不合理收费等，并表达不满情绪（如"不满意"、"问题太多"、"影响业务"等），请将其分类为 "Complaint"。  

**关键词**（可作为辅助）：  
不满意、问题太多、错误、影响业务、服务不好、延迟、未按承诺交付、不合理收费、重复问题。  

---

#### **6. 愤怒（Angry）**  
**描述**：  
请分析以下邮件内容，判断是否包含强烈的愤怒情绪。如果邮件使用了强烈的负面词汇（如 "完全无法接受"、"非常愤怒"、"极其失望"），或者邮件语气极端，表明客户对问题极度不满，请将其分类为 "Angry"。  

**关键词**（可作为辅助）：  
愤怒、无法接受、极其失望、严重影响、投诉、太糟糕、绝对不行、愚蠢的决定、荒谬、不负责任。  

---

### **技术支持分类提示词**  

#### **7. 技术支持（Technical Support）**  
**描述**：  
请分析以下邮件内容，判断是否包含技术相关的问题或咨询。如果邮件涉及系统故障、软件错误、技术配置、接口问题、API 调用失败、技术操作指南等内容，请将其分类为 "Technical Support"。  

**关键词**（可作为辅助）：  
系统故障、软件错误、无法访问、技术问题、配置失败、接口调用、API 请求失败、技术指南、服务器错误、代码问题、数据库查询、系统维护、功能异常。  

---




我有这样一个表，

create table asset.cc_emailclassifyrule (
  id bigint not null
  , created_at timestamp(6) with time zone not null
  , updated_at timestamp(6) with time zone not null
  , name character varying(100) not null
  , description text not null
  , sender_domains jsonb not null
  , subject_keywords jsonb not null
  , body_keywords jsonb not null
  , min_attachments integer not null
  , max_attachments integer
  , min_attachment_size bigint not null
  , max_attachment_size bigint
  , classification character varying(100) not null
  , priority integer not null
  , is_active boolean not null
  , primary key (id)
);

要定义对以下classification的分类定义内容，

order
billing
cash
collection
complain
angry
techsupport

id从5开始，name 和classification 定义为以上的分类名，description 分别为

#### **1. Order（订单相关）**  
**描述**：  
请分析以下邮件内容，判断是否与订单处理相关。如果邮件涉及订单录入、订单验证、库存检查、价格确认、信用检查、订单执行、订单拣选、物流安排、出货确认等内容，请将其分类为 "Order"。  

**关键词**（可作为辅助）：  
订单录入、订单验证、库存检查、价格确认、付款条件、信用检查、拣选、包装、物流安排、发货、库存保留、出货确认。  

---

#### **2. Billing（发票相关）**  
**描述**：  
请分析以下邮件内容，判断是否与发票开具相关。如果邮件涉及发票生成、发票发送、商品明细、税金计算、付款条款、账务联动等内容，请将其分类为 "Billing"。  

**关键词**（可作为辅助）：  
发票、账单、应收发票、税金计算、付款条款、客户账单、财务凭证、账务调整。  

---

#### **3. Cash（应收账款 & 现金对账相关）**  
**描述**：  
请分析以下邮件内容，判断是否与应收账款或现金对账相关。如果邮件涉及发票跟踪、应收账款到期管理、客户付款匹配、部分付款、扣款处理、财务对账等内容，请将其分类为 "Cash"。  

**关键词**（可作为辅助）：  
应收账款、发票状态、到期日、付款匹配、部分付款、全额付款、扣款、财务对账、收款核销。  

---

#### **4. Collections（催收 & 扣款管理相关）**  
**描述**：  
请分析以下邮件内容，判断是否与催收或扣款管理相关。如果邮件涉及逾期未付款的催收、客户扣款争议、付款提醒、信用额度管理、贷项余额调整等内容，请将其分类为 "Collections"。  

**关键词**（可作为辅助）：  
催收、逾期账款、付款提醒、扣款争议、贷项余额、信用额度、未支付发票、客户催款、违约金。  

---

### **情感分类提示词**  

#### **5. 抱怨（Complaint）**  
**描述**：  
请分析以下邮件内容，判断是否包含客户的抱怨或不满情绪。如果邮件中提到服务质量问题、交付延误、错误账单、不合理收费等，并表达不满情绪（如"不满意"、"问题太多"、"影响业务"等），请将其分类为 "Complaint"。  

**关键词**（可作为辅助）：  
不满意、问题太多、错误、影响业务、服务不好、延迟、未按承诺交付、不合理收费、重复问题。  

---

#### **6. 愤怒（Angry）**  
**描述**：  
请分析以下邮件内容，判断是否包含强烈的愤怒情绪。如果邮件使用了强烈的负面词汇（如 "完全无法接受"、"非常愤怒"、"极其失望"），或者邮件语气极端，表明客户对问题极度不满，请将其分类为 "Angry"。  

**关键词**（可作为辅助）：  
愤怒、无法接受、极其失望、严重影响、投诉、太糟糕、绝对不行、愚蠢的决定、荒谬、不负责任。  

请帮我生成你能想到的sender_domains，subject_keywords，body_keywords，的内容，格式为["xxx", "xxx2"]，attachments内容都为空，priority从7开始，is_active为true




我要同时取出表 cc_forwardingaddress的name字段
在页面MonitoringDetailModal.tsx 分类统计部分，
在分类，邮件件数后，添加邮件送信地址名，表 cc_forwardingaddress的name字段。
例如，[OTC Billing: 6 封 账单管理组] 这样的格式


帮我设计两套配置，亮色，暗色，可以通开关切换。


1. 重新设计一下这个页面的配色，字体，更漂亮一些。
2. 分类统计部分，
    1. 按照固定的排列顺序。分三列显示。
    2. 每个项目的意思是，分类名，识别到这个分类的邮件数，分配这类邮件给谁处理。请帮我设计出可以表达这个意思的页面表现风格。
3. 邮件监控详情部分，监控师，表示监控接收邮件的进度。处理智能体，表示分类处理邮件的进度。再添加一个，分配任务智能体，表示处理邮件（现在是转发）的进度。

请先帮我修改前端页面设计。后端稍后再修改。

我要在一个页面完整显示。不做滚动。
1. 整体宽度改成1280.
1. 邮件监控详情 的三个进度的间隔改小。
2. 分类统计 部分的每个分类信息的宽度改小。改成三列显示。


1. 亮色，暗色，的切换开关，放到外层页面，login, chatpage, mailconfigpage 都实现这两个风格。
2. 暗色时，黑色字体看不出来了如图。需要调节。



后端添加 assigned_emails 变量到前端。要求， 
    1. 后端记录，1 总邮件数，2. 接收完成的邮件总数，3. 分类完成的邮件总数。4. 转发完成的邮件总数。
    2. 前端的各个进度如下：
    监控师 接收完成的邮件总数 /总邮件数
    邮件分析师 分类完成的邮件总数 /总邮件数
    任务分配专员 转发完成的邮件总数 /总邮件数


前端的 forwarded_emails 的数量是0，是不是也应该在表 cc_email 中记录，使用is_forwarded这个字段。
