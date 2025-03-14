# Generated by Django 5.0.2 on 2025-03-06 07:00

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CCAzureOpenAI",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "name",
                    models.CharField(max_length=100, unique=True, verbose_name="模型名称"),
                ),
                ("model_id", models.CharField(max_length=100, verbose_name="模型ID")),
                ("endpoint", models.URLField(max_length=255, verbose_name="API端点")),
                ("api_key", models.CharField(max_length=255, verbose_name="API密钥")),
                (
                    "api_version",
                    models.CharField(
                        blank=True, max_length=50, null=True, verbose_name="API版本"
                    ),
                ),
                ("temperature", models.FloatField(default=0.7, verbose_name="温度参数")),
                (
                    "max_tokens",
                    models.IntegerField(default=2000, verbose_name="最大token数"),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="是否激活")),
                ("provider", models.CharField(max_length=50, verbose_name="提供商")),
                ("description", models.TextField(blank=True, verbose_name="描述")),
                (
                    "deployment_name",
                    models.CharField(max_length=100, verbose_name="部署名称"),
                ),
                (
                    "resource_name",
                    models.CharField(max_length=100, verbose_name="资源名称"),
                ),
            ],
            options={
                "verbose_name": "Azure OpenAI配置",
                "verbose_name_plural": "Azure OpenAI配置",
                "db_table": "cc_azure_openai",
            },
        ),
        migrations.CreateModel(
            name="CCOpenAI",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "name",
                    models.CharField(max_length=100, unique=True, verbose_name="模型名称"),
                ),
                ("model_id", models.CharField(max_length=100, verbose_name="模型ID")),
                ("endpoint", models.URLField(max_length=255, verbose_name="API端点")),
                ("api_key", models.CharField(max_length=255, verbose_name="API密钥")),
                (
                    "api_version",
                    models.CharField(
                        blank=True, max_length=50, null=True, verbose_name="API版本"
                    ),
                ),
                ("temperature", models.FloatField(default=0.7, verbose_name="温度参数")),
                (
                    "max_tokens",
                    models.IntegerField(default=2000, verbose_name="最大token数"),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="是否激活")),
                ("provider", models.CharField(max_length=50, verbose_name="提供商")),
                ("description", models.TextField(blank=True, verbose_name="描述")),
                (
                    "organization_id",
                    models.CharField(
                        blank=True, max_length=100, null=True, verbose_name="组织ID"
                    ),
                ),
            ],
            options={
                "verbose_name": "OpenAI配置",
                "verbose_name_plural": "OpenAI配置",
                "db_table": "cc_openai",
            },
        ),
    ]
