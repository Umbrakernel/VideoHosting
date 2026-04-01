# api/serializers.py

from rest_framework import serializers
from .models import Video # Убедитесь, что этот импорт нужен, если VideoSerializer здесь
from .models import Comment
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

REQUIRED_ACCESS_CODE = "GOOL+GOIDA"

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']
        read_only_fields = ['id', 'date_joined']

class VideoSerializer(serializers.ModelSerializer):
    author_username = serializers.ReadOnlyField(source='author.username')
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            'id',
            'title',
            'description',
            'video',
            'file_url',
            'author',
            'author_username',
            'uploaded_at',
            'thumbnail'
        ]
        read_only_fields = ['author', 'uploaded_at', 'thumbnail']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.video and request:
            return request.build_absolute_uri(obj.video.url)
        return None

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)

class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password]
    )
    password2 = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        required=True
    )
    access_code = serializers.CharField(
        write_only=True, 
        required=True
    )


    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'access_code')
        # Убеждаемся, что email обязателен
        extra_kwargs = {
            'email': {'required': True}
        }

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password2'):
            raise serializers.ValidationError({"password": "Пароли не совпадают"})

        if User.objects.filter(email=attrs.get('email')).exists():
             raise serializers.ValidationError({"email": "Этот email уже используется"})

        provided_code = attrs.get('access_code')

        if not provided_code or provided_code != REQUIRED_ACCESS_CODE:
            raise serializers.ValidationError({"access_code": "Неверный или отсутствует код доступа."})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password2', None)
        validated_data.pop('access_code', None)

        user = User.objects.create_user(**validated_data)
        return user
class CommentSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Comment
        fields = ['id', 'video', 'author', 'text', 'created_at']
        read_only_fields = ['id', 'video', 'author', 'created_at']
