from rest_framework import serializers

from core.models import User


class UserBriefSerializer(serializers.ModelSerializer):
    """Trimmed-down user representation for nesting inside Ride payloads."""

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "phone_number", "role"]


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "role",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
