from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from user_profile.auth_serializers import (
    EmailOrUsernameTokenObtainPairSerializer,
    RegisterSerializer,
    UserSerializer,
    ChangePasswordSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class EmailOrUsernameLoginView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenObtainPairSerializer


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Password changed successfully."})
        return Response(serializer.errors, status=400)
