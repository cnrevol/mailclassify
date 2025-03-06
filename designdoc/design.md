
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


    1. 通过邮件地址，读取outlook邮件接口。
        参数 邮件地址，最新邮件个数-读取这个个数的最新邮件，时间（小时）读取这个时间范围内的最新邮件。
        返回值，邮件类，包含邮件关键信息，包括但不限于，邮件id,邮件标题，内容，发信地址，收信时间，
    使用azure graph api 读取outlook邮件，认证需要的 azure client id,azure client secret, 从数据库表中取得，表名 cc_user_info, 字段包括userid, client_id, cilent_secret.
    读取过的邮件标记为已读。


    2.对邮件内容分类的接口
        参数  