from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from .serializers import RegisterSerializer

@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    s = RegisterSerializer(data=request.data)
    if s.is_valid():
        user = s.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"user_id": user.id, "username": user.username, "token": token.key}, status=201)
    return Response(s.errors, status=400)

class CustomObtainAuthToken(ObtainAuthToken):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if "token" in response.data:
            token = Token.objects.get(key=response.data["token"])
            user  = token.user
            return Response({"token": token.key, "user_id": user.id, "username": user.username})
        return Response({"detail": "Invalid credentials"}, status=400)

@api_view(["POST"])
def logout_view(request):
    user = request.user
    if not user.is_authenticated:
        return Response({"detail":"User is not authenticated"}, status=401)
    Token.objects.filter(user=user).delete()
    return Response({"detail":"Logged out successfully"})
