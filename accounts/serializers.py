from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import User, Profile

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("avatar", "timezone", "preferences")

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "profile", "date_joined")
        read_only_fields = ("id", "date_joined")

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name", "role")

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(**validated_data, password=password)
        return user

class UpdateMeSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=User.Roles.choices, required=False)
    timezone = serializers.CharField(required=False)
    preferences = serializers.JSONField(required=False)
    avatar = serializers.ImageField(required=False)

    def validate(self, attrs):
        f = attrs.get("avatar")
        if f:
            max_bytes = 2 * 1024 * 1024  # 2MB
            if hasattr(f, 'size') and f.size > max_bytes:
                raise ValidationError({"avatar": "Maximum size is 2MB."})
            ctype = getattr(f, 'content_type', '')
            if ctype and ctype not in ("image/jpeg", "image/png", "image/webp"):
                raise ValidationError({"avatar": "Only JPEG/PNG/WEBP allowed."})
        return attrs

    def update(self, instance, validated_data):
        for field in ("first_name", "last_name", "role"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()

        profile = instance.profile
        if 'timezone' in validated_data:
            profile.timezone = validated_data['timezone']
        if 'preferences' in validated_data:
            profile.preferences = validated_data['preferences']
        if 'avatar' in validated_data:
            profile.avatar = validated_data['avatar']
        profile.save()
        return instance

    def to_representation(self, instance):
        return UserSerializer(instance).data