from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import CCUserMailInfo, CCAzureOpenAI, CCOpenAI, CCEmail
import logging

logger = logging.getLogger(__name__)

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')

class CCEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CCEmail
        fields = (
            'id', 'message_id', 'subject', 'sender', 'received_time',
            'content', 'is_read', 'categories', 'importance',
            'has_attachments', 'created_at', 'updated_at'
        )
        read_only_fields = fields

class CCUserMailInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CCUserMailInfo
        fields = (
            'id', 'email', 'client_id', 'client_secret', 'tenant_id',
            'last_sync_time', 'is_active', 'created_at', 'updated_at'
        )
        extra_kwargs = {
            'client_secret': {'write_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True}
        }

    def create(self, validated_data):
        logger.info(f"Creating new mail info for: {validated_data.get('email')}")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        logger.info(f"Updating mail info for: {instance.email}")
        return super().update(instance, validated_data)

class CCAzureOpenAISerializer(serializers.ModelSerializer):
    class Meta:
        model = CCAzureOpenAI
        fields = (
            'id', 'name', 'model_id', 'endpoint', 'api_version',
            'temperature', 'max_tokens', 'is_active', 'provider',
            'description', 'deployment_name', 'resource_name',
            'created_at', 'updated_at'
        )
        extra_kwargs = {
            'api_key': {'write_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True}
        }

    def create(self, validated_data):
        logger.info(f"Creating new Azure OpenAI config: {validated_data.get('name')}")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        logger.info(f"Updating Azure OpenAI config: {instance.name}")
        return super().update(instance, validated_data)

class CCOpenAISerializer(serializers.ModelSerializer):
    class Meta:
        model = CCOpenAI
        fields = (
            'id', 'name', 'model_id', 'endpoint', 'api_version',
            'temperature', 'max_tokens', 'is_active', 'provider',
            'description', 'organization_id', 'created_at', 'updated_at'
        )
        extra_kwargs = {
            'api_key': {'write_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True}
        }

    def create(self, validated_data):
        logger.info(f"Creating new OpenAI config: {validated_data.get('name')}")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        logger.info(f"Updating OpenAI config: {instance.name}")
        return super().update(instance, validated_data) 