
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

    