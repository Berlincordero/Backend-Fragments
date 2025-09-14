from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile

class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model  = Profile
        fields = ["id","username","display_name","bio","date_of_birth","gender","avatar","cover","updated_at"]
        read_only_fields = ["id","username","updated_at"]

class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField()
    email    = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, min_length=6)

    date_of_birth = serializers.DateField(required=False)
    gender        = serializers.ChoiceField(choices=Profile.GENDER_CHOICES, required=False)

    class Meta:
        model  = User
        fields = ["username","email","password","date_of_birth","gender"]

    def create(self, validated_data):
        dob    = validated_data.pop("date_of_birth", None)
        gender = validated_data.pop("gender", "")

        user = User.objects.create_user(
            username = validated_data["username"],
            email    = validated_data.get("email", ""),
            password = validated_data["password"],
        )
        Profile.objects.update_or_create(
            user=user, defaults={"date_of_birth": dob, "gender": gender}
        )
        return user
