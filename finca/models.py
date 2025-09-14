# modulo/finca/models.py
from django.db import models
from django.contrib.auth.models import User


def user_directory_path(instance, filename):
    """
    Soporta Profile (tiene 'user'), Post (tiene 'author') y CoverSlide (tiene 'user').
    Usamos *_id para no tocar la relación.
    """
    uid = getattr(instance, "user_id", None) or getattr(instance, "author_id", None)
    if uid is None:
        raise ValueError(f"user_directory_path: objeto sin user/author -> {instance!r}")
    return f"finca_{uid}/{filename}"


class Profile(models.Model):
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name="finca_profile")
    display_name = models.CharField(max_length=100, blank=True)
    bio          = models.TextField(blank=True)
    avatar       = models.ImageField(upload_to=user_directory_path, blank=True, null=True)
    cover        = models.ImageField(upload_to=user_directory_path, blank=True, null=True)
    updated_at   = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Finca de {self.user.username}"


class Post(models.Model):
    author     = models.ForeignKey(User, on_delete=models.CASCADE, related_name="finca_posts")
    text       = models.TextField(blank=True)
    image      = models.ImageField(upload_to=user_directory_path, blank=True, null=True)
    video      = models.FileField(upload_to=user_directory_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # 🔁 Cuando el post es un “repost”, apunta al post original.
    repost_of  = models.ForeignKey("self", null=True, blank=True,
                                   on_delete=models.CASCADE, related_name="reposts")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        preview = self.text[:30] if self.text else "📎 media"
        return f"{self.author.username}: {preview}"


class PostStar(models.Model):
    """Una estrella por (usuario, post)."""
    post       = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="stars")
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="finca_stars")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"⭐ {self.user.username} -> post {self.post_id}"


class Comment(models.Model):
    post       = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="finca_comments")
    parent     = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    text       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"💬 {self.user.username} -> post {self.post_id} ({self.text[:30]!r})"


class PostWhatsAppShare(models.Model):
    """
    Un registro por (usuario, post) que haya compartido por WhatsApp.
    Idempotente: no se duplica para el mismo par usuario/post.
    """
    post       = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="whatsapp_shares")
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="finca_whatsapp_shares")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"📲 {self.user.username} -> post {self.post_id}"


class PostSave(models.Model):
    """Un guardado por (usuario, post)."""
    post       = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="saves")
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="finca_saves")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"🔖 {self.user.username} -> post {self.post_id}"


# ========= NUEVO: Carrusel de portada (hasta 3 imágenes) =========
class CoverSlide(models.Model):
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="finca_cover_slides")
    index        = models.PositiveSmallIntegerField()  # 0..2
    image        = models.ImageField(upload_to=user_directory_path, blank=True, null=True)
    caption      = models.TextField(blank=True)        # párrafo común
    bibliography = models.CharField(max_length=255, blank=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "index")
        ordering = ["index"]

    def __str__(self):
        return f"CoverSlide idx={self.index} user={self.user_id}"
