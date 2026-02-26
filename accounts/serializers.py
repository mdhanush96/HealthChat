from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    age = serializers.IntegerField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=["male", "female", "other"], required=False, allow_blank=True
    )

    class Meta:
        model = User
        fields = ("username", "email", "password", "age", "gender")

    def create(self, validated_data):
        age = validated_data.pop("age", None)
        gender = validated_data.pop("gender", "")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )
        UserProfile.objects.create(user=user, age=age, gender=gender)
        return user


class UserSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "age", "gender")

    def get_age(self, obj):
        try:
            return obj.profile.age
        except UserProfile.DoesNotExist:
            return None

    def get_gender(self, obj):
        try:
            return obj.profile.gender
        except UserProfile.DoesNotExist:
            return ""
