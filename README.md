# mailclassify

# 20230318

EmailMonitorConsumer (consumers.py)
└── monitoring_loop
    └── EmailMonitorService.check_new_emails (email_monitor.py)
        ├── OutlookMailService.fetch_emails
        ├── EmailClassifier.classify_emails (email_classifier.py)
        │   ├── load_email_categories
        │   └── EmailClassificationAgent
        │       ├── _stepgo_classify
        │       ├── _single_classify
        │       └── _ensemble_classify
        └── EmailForwardingService.process_classified_emails (email_forwarding.py)
            └── mail_service.forward_email






# 1. 激活虚拟环境
cd C:\worksapce\aifree\ContentsClassification\project\prj1

venv\Scripts\activate

venv\Scripts\activate

# 2. 切换到项目目录
cd C:\worksapce\aifree\ContentsClassifyProject\mailclassify\backend

# 3. 启动服务器
python manage.py runserver

python manage.py makemigrations
python manage.py migrate

python manage.py migrate core 0005_ccemailforwardinglog_ccforwardingrule_and_more --fake

python manage.py migrate core 0006_ccemail_classification_confidence_and_more --fake
   python manage.py migrate --fake-initial
      python manage.py sqlmigrate core 0005_ccemailforwardinglog_ccforwardingrule_and_more

daphne -b 0.0.0.0 -p 8000 config.asgi:application
