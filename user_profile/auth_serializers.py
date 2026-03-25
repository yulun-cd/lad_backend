from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]
        read_only_fields = ["id", "username", "email"]


class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field].required = False

    def validate(self, attrs):
        login_value = attrs.get(self.username_field) or attrs.get("email")
        if not login_value:
            raise serializers.ValidationError(
                {self.username_field: ["This field is required."]}
            )

        user_model = get_user_model()

        try:
            user = user_model.objects.get(username__iexact=login_value)
        except user_model.DoesNotExist:
            users_by_email = user_model.objects.filter(email__iexact=login_value)
            if users_by_email.count() == 1:
                user = users_by_email.first()
            else:
                user = None

        if user is not None:
            attrs[self.username_field] = user.get_username()

        return super().validate(attrs)
