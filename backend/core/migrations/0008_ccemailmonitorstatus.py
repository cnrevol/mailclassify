# Generated by Django 5.0.2 on 2025-03-09 14:37

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_auto_20250309_1407"),
    ]

    operations = [
        migrations.CreateModel(
            name="CCEmailMonitorStatus",
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
                    "email",
                    models.CharField(max_length=255, unique=True, verbose_name="邮箱地址"),
                ),
                (
                    "is_monitoring",
                    models.BooleanField(default=False, verbose_name="是否正在监控"),
                ),
                (
                    "last_check_time",
                    models.DateTimeField(blank=True, null=True, verbose_name="上次检查时间"),
                ),
                (
                    "last_found_emails",
                    models.IntegerField(default=0, verbose_name="上次发现的新邮件数"),
                ),
                (
                    "total_classified_emails",
                    models.IntegerField(default=0, verbose_name="总分类邮件数"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
            ],
            options={
                "verbose_name": "邮件监控状态",
                "verbose_name_plural": "邮件监控状态",
                "db_table": "cc_email_monitor_status",
            },
        ),
    ]
