-- 插入Azure OpenAI配置
INSERT INTO cc_azure_openai (
    name,
    model_id,
    endpoint,
    api_key,
    api_version,
    temperature,
    max_tokens,
    is_active,
    provider,
    description,
    deployment_name,
    resource_name,
    created_at,
    updated_at
) VALUES (
    'Azure GPT-4',
    'gpt-4o',  -- 使用提供的模型名称
    'https://aicontents.openai.azure.com/',  -- 使用提供的端点
    'your-api-key-here',  -- 需要替换为实际的API密钥
    '2024-08-01-preview',  -- 使用提供的API版本
    0.7,  -- 使用提供的温度值
    1000,  -- 使用提供的最大token数
    true,
    'azure',
    'Azure OpenAI GPT-4模型',
    'gpt-4o',  -- 使用相同的部署名称
    'aicontents',  -- 从URL中提取的资源名称
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
); 