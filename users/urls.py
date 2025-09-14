from django.urls import path
from .views import register_view, logout_view, CustomObtainAuthToken

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', CustomObtainAuthToken.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
]
