from django.db import models
from django.contrib.auth.models import User

def user_directory_path(instance, filename):
    return f"profile_{instance.user.id}/{filename}"

class Profile(models.Model):
    GENDER_CHOICES = [("M","Masculino"), ("F","Femenino"), ("O","Otro")]

    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name  = models.CharField(max_length=100, blank=True)
    bio           = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender        = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    avatar        = models.ImageField(upload_to=user_directory_path, blank=True, null=True)
    cover         = models.ImageField(upload_to=user_directory_path, blank=True, null=True)
    updated_at    = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"
