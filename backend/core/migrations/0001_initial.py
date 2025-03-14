# Generated by Django 5.0.2 on 2025-03-06 06:18

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CCUserMailInfo",
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
                    "email",
                    models.EmailField(max_length=255, unique=True, verbose_name="邮箱地址"),
                ),
                ("client_id", models.CharField(max_length=255, verbose_name="客户端ID")),
                (
                    "client_secret",
                    models.CharField(max_length=255, verbose_name="客户端密钥"),
                ),
                ("password", models.CharField(max_length=255, verbose_name="登录密码")),
                ("is_active", models.BooleanField(default=True, verbose_name="是否激活")),
            ],
            options={
                "verbose_name": "用户邮件信息",
                "verbose_name_plural": "用户邮件信息",
                "db_table": "cc_usermail_info",
            },
        ),
    ]
