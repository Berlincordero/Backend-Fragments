# modulo/finca/serializers.py
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from .models import (
    Profile, Post, PostStar, Comment, PostWhatsAppShare, PostSave, CoverSlide
)


def abs_url(request, filefield):
    """Devuelve URL absoluta para un File/ImageField o None."""
    if not filefield:
        return None
    url = filefield.url
    return request.build_absolute_uri(url) if request else url


# ===== PROFILE =====
class ProfileSerializer(serializers.ModelSerializer):
    username      = serializers.ReadOnlyField(source="user.username")
    email         = serializers.ReadOnlyField(source="user.email")
    date_of_birth = serializers.SerializerMethodField()
    gender        = serializers.SerializerMethodField()

    avatar = serializers.ImageField(required=False, allow_null=True)
    cover  = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model  = Profile
        fields = [
            "id", "username", "email", "display_name", "bio",
            "date_of_birth", "gender", "avatar", "cover", "updated_at",
        ]
        read_only_fields = ["id", "username", "email", "updated_at"]

    def get_date_of_birth(self, obj):
        dob = getattr(obj.user, "profile", None)
        dob = getattr(dob, "date_of_birth", None)
        return dob.isoformat() if dob else None

    def get_gender(self, obj):
        prof = getattr(obj.user, "profile", None)
        return getattr(prof, "gender", None)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        data["avatar"] = abs_url(request, instance.avatar)
        data["cover"]  = abs_url(request, instance.cover)
        return data


def _user_preview(user, request):
    """Nombre visible y avatar para listados (stars, comments, shares, reposts, saves)."""
    try:
        fp = user.finca_profile
    except ObjectDoesNotExist:
        fp, _ = Profile.objects.get_or_create(user=user)
    return {
        "username": user.username,
        "display_name": fp.display_name or user.username,
        "avatar": abs_url(request, fp.avatar),
    }


# ===== COMMENTS =====
class CommentSerializer(serializers.ModelSerializer):
    user    = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    parent  = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model  = Comment
        fields = ["id", "text", "created_at", "parent", "user", "replies"]

    def get_user(self, obj):
        return _user_preview(obj.user, self.context.get("request"))

    def get_replies(self, obj):
        qs = obj.replies.select_related("user", "user__finca_profile").order_by("created_at")
        return CommentSerializer(qs, many=True, context=self.context).data


# ===== POST =====
class PostSerializer(serializers.ModelSerializer):
    author        = serializers.SerializerMethodField()
    content       = serializers.CharField(source="text", allow_blank=True, required=False)

    image         = serializers.ImageField(required=False, allow_null=True)
    video         = serializers.FileField(required=False, allow_null=True)

    # 🔁 REPOST
    repost_of       = serializers.SerializerMethodField()
    reposts_count   = serializers.SerializerMethodField()
    has_reposted    = serializers.SerializerMethodField()
    repost_sample   = serializers.SerializerMethodField()
    first_reposter  = serializers.SerializerMethodField()

    # ⭐
    stars_count   = serializers.SerializerMethodField()
    has_starred   = serializers.SerializerMethodField()
    stars_sample  = serializers.SerializerMethodField()
    first_starrer = serializers.SerializerMethodField()

    # 💬
    comments_count = serializers.SerializerMethodField()

    # 📲 WhatsApp
    whatsapp_count       = serializers.SerializerMethodField()
    has_shared_whatsapp  = serializers.SerializerMethodField()
    whatsapp_sample      = serializers.SerializerMethodField()
    first_whatsapper     = serializers.SerializerMethodField()

    # 🔖 Guardados
    saves_count   = serializers.SerializerMethodField()
    has_saved     = serializers.SerializerMethodField()
    saves_sample  = serializers.SerializerMethodField()
    first_saver   = serializers.SerializerMethodField()

    class Meta:
        model  = Post
        fields = [
            "id", "author", "content", "image", "video", "created_at",
            # 🔁 REPOST
            "repost_of", "reposts_count", "has_reposted", "repost_sample", "first_reposter",
            # ⭐
            "stars_count", "has_starred", "stars_sample", "first_starrer",
            # 💬
            "comments_count",
            # 📲 WhatsApp
            "whatsapp_count", "has_shared_whatsapp", "whatsapp_sample", "first_whatsapper",
            # 🔖 Guardados
            "saves_count", "has_saved", "saves_sample", "first_saver",
        ]

    # ------- autor -------
    def get_author(self, obj):
        request = self.context.get("request")
        try:
            prof = obj.author.finca_profile
        except ObjectDoesNotExist:
            prof, _ = Profile.objects.get_or_create(user=obj.author)
        return {
            "username": obj.author.username,
            "display_name": prof.display_name or obj.author.username,
            "avatar": abs_url(request, prof.avatar),
        }

    # ------- 🔁 REPOST -------
    def get_repost_of(self, obj):
        if not obj.repost_of_id:
            return None
        orig = obj.repost_of
        request = self.context.get("request")
        try:
            prof = orig.author.finca_profile
        except ObjectDoesNotExist:
            prof, _ = Profile.objects.get_or_create(user=orig.author)
        return {
            "id": orig.id,
            "author": {
                "username": orig.author.username,
                "display_name": prof.display_name or orig.author.username,
                "avatar": abs_url(request, prof.avatar),
            },
            "content": orig.text,
            "image": abs_url(request, orig.image),
            "video": abs_url(request, orig.video),
            "created_at": orig.created_at,
        }

    def get_reposts_count(self, obj):
        return getattr(obj, "reposts_count", None) or obj.reposts.count()

    def get_has_reposted(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return Post.objects.filter(author=user, repost_of=obj).exists()

    def get_repost_sample(self, obj):
        request = self.context.get("request")
        qs = obj.reposts.select_related("author", "author__finca_profile").order_by("-created_at")[:3]
        return [_user_preview(r.author, request) for r in qs]

    def get_first_reposter(self, obj):
        request = self.context.get("request")
        first = obj.reposts.select_related("author", "author__finca_profile").order_by("created_at").first()
        return _user_preview(first.author, request) if first else None

    # ------- ⭐ -------
    def get_stars_count(self, obj):
        return getattr(obj, "stars_count", None) or obj.stars.count()

    def get_has_starred(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return PostStar.objects.filter(post=obj, user=user).exists()

    def get_stars_sample(self, obj):
        request = self.context.get("request")
        qs = obj.stars.select_related("user", "user__finca_profile").order_by("-created_at")[:3]
        return [_user_preview(s.user, request) for s in qs]

    def get_first_starrer(self, obj):
        request = self.context.get("request")
        first = (
            obj.stars.select_related("user", "user__finca_profile")
            .order_by("created_at")
            .first()
        )
        if not first:
            return None
        return _user_preview(first.user, request)

    # ------- 💬 -------
    def get_comments_count(self, obj):
        return getattr(obj, "comments_count", None) or obj.comments.count()

    # ------- 📲 WhatsApp -------
    def get_whatsapp_count(self, obj):
        return getattr(obj, "whatsapp_count", None) or obj.whatsapp_shares.count()

    def get_has_shared_whatsapp(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return PostWhatsAppShare.objects.filter(post=obj, user=user).exists()

    def get_whatsapp_sample(self, obj):
        request = self.context.get("request")
        qs = obj.whatsapp_shares.select_related("user", "user__finca_profile").order_by("-created_at")[:3]
        return [_user_preview(s.user, request) for s in qs]

    def get_first_whatsapper(self, obj):
        request = self.context.get("request")
        first = (
            obj.whatsapp_shares.select_related("user", "user__finca_profile")
            .order_by("created_at")
            .first()
        )
        return _user_preview(first.user, request) if first else None

    # ------- 🔖 GUARDADOS -------
    def get_saves_count(self, obj):
        return getattr(obj, "saves_count", None) or obj.saves.count()

    def get_has_saved(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return PostSave.objects.filter(post=obj, user=user).exists()

    def get_saves_sample(self, obj):
        request = self.context.get("request")
        qs = obj.saves.select_related("user", "user__finca_profile").order_by("-created_at")[:3]
        return [_user_preview(s.user, request) for s in qs]

    def get_first_saver(self, obj):
        request = self.context.get("request")
        first = (
            obj.saves.select_related("user", "user__finca_profile")
            .order_by("created_at")
            .first()
        )
        return _user_preview(first.user, request) if first else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        data["image"] = abs_url(request, instance.image)
        data["video"] = abs_url(request, instance.video)
        return data


# ===== COVER SLIDES =====
class CoverSlideSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model  = CoverSlide
        fields = [
            "id", "index", "image", "caption", "bibliography",
            "text_color", "text_font", "text_x", "text_y", "text_size", "effect",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        data["image"] = abs_url(request, instance.image)
        return data
