# finca/views.py
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Profile, Post, PostStar, Comment, PostWhatsAppShare, PostSave, CoverSlide
from .serializers import (
    ProfileSerializer, PostSerializer, CommentSerializer, abs_url, CoverSlideSerializer
)


# --------- Permisos básicos ---------
class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return getattr(obj, "user", None) == request.user


class IsAuthor(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return getattr(obj, "author", None) == request.user


class IsCommentOwnerOrPostAuthor(permissions.BasePermission):
    def has_object_permission(self, request, view, obj: Comment):
        return (obj.user_id == request.user.id) or (obj.post.author_id == request.user.id)


# ---------- PERFIL (mi finca) ----------
class MyFincaViewSet(viewsets.ModelViewSet):
    serializer_class   = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    parser_classes     = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def get_object(self):
        perfil, _ = Profile.objects.get_or_create(user=self.request.user)
        return perfil

    def list(self, request, *args, **kwargs):
        ser = self.get_serializer(self.get_object())
        return Response(ser.data)

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        # permitimos POST como "update" parcial del perfil del usuario
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


# ---------- POSTS ----------
class PostViewSet(viewsets.ModelViewSet):
    """
    /api/finca/posts/        GET, POST  (solo mis posts)
    /api/finca/posts/<id>/   PATCH, DELETE (solo autor)
    /api/finca/feed/         GET (todos los posts)
    /api/finca/saved/        GET (posts guardados por el usuario)
    /api/finca/posts/<id>/star/         POST (toggle)
    /api/finca/posts/<id>/starrers/     GET  (listado usuarios)
    /api/finca/posts/<id>/comments/     GET, POST (árbol / crear)
    /api/finca/posts/<id>/whatsapp/     POST (registrar share idempotente)
    /api/finca/posts/<id>/whatsappers/  GET  (listado usuarios)
    /api/finca/posts/<id>/repost/       POST (crear/obtener repost propio)
    /api/finca/posts/<id>/reposters/    GET  (listado usuarios que compartieron)
    /api/finca/posts/<id>/save/         POST (toggle guardado)
    /api/finca/posts/<id>/savers/       GET  (listado usuarios que guardaron)
    """
    serializer_class   = PostSerializer
    permission_classes = [permissions.IsAuthenticated, IsAuthor]
    parser_classes     = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    # listado por defecto: SOLO mis posts
    def get_queryset(self):
        return (
            Post.objects
            .filter(author=self.request.user)
            .select_related("author")
            .prefetch_related(
                # 🔁
                "reposts__author", "reposts__author__finca_profile",
                # ⭐
                "stars__user", "stars__user__finca_profile",
                # 💬
                "comments__user", "comments__user__finca_profile",
                # 📲
                "whatsapp_shares__user", "whatsapp_shares__user__finca_profile",
                # 🔖
                "saves__user", "saves__user__finca_profile",
            )
            .annotate(
                comments_count=Count("comments"),
                whatsapp_count=Count("whatsapp_shares"),
                reposts_count=Count("reposts"),
                saves_count=Count("saves"),
            )
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.check_object_permissions(request, instance)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # -------- FEED GLOBAL --------
    @action(detail=False, methods=["get"], url_path="feed",
            permission_classes=[permissions.IsAuthenticated])
    def feed(self, request):
        qs = (
            Post.objects
            .select_related("author")
            .prefetch_related(
                "reposts__author", "reposts__author__finca_profile",
                "stars__user", "stars__user__finca_profile",
                "comments__user", "comments__user__finca_profile",
                "whatsapp_shares__user", "whatsapp_shares__user__finca_profile",
                "saves__user", "saves__user__finca_profile",
            )
            .annotate(
                stars_count=Count("stars"),
                comments_count=Count("comments"),
                whatsapp_count=Count("whatsapp_shares"),
                reposts_count=Count("reposts"),
                saves_count=Count("saves"),
            )
            .order_by("-created_at")
        )
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    # -------- LISTA DE GUARDADOS --------
    @action(detail=False, methods=["get"], url_path="saved",
            permission_classes=[permissions.IsAuthenticated])
    def saved(self, request):
        """
        Lista las publicaciones que el usuario autenticado ha guardado.
        Ordenadas por fecha de guardado (más reciente primero).
        """
        qs = (
            Post.objects
            .filter(saves__user=request.user)
            .select_related("author")
            .prefetch_related(
                "reposts__author", "reposts__author__finca_profile",
                "stars__user", "stars__user__finca_profile",
                "comments__user", "comments__user__finca_profile",
                "whatsapp_shares__user", "whatsapp_shares__user__finca_profile",
                "saves__user", "saves__user__finca_profile",
            )
            .annotate(
                stars_count=Count("stars"),
                comments_count=Count("comments"),
                whatsapp_count=Count("whatsapp_shares"),
                reposts_count=Count("reposts"),
                saves_count=Count("saves"),
            )
            .order_by("-saves__created_at", "-created_at")
        )
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(ser.data)
        return Response(ser.data)

    # -------- REACCIONES (⭐) --------
    @action(detail=True, methods=["post"], url_path="star",
            permission_classes=[permissions.IsAuthenticated])
    def star(self, request, pk=None):
        """
        Toggle de estrella para el usuario autenticado sobre el post <pk>.
        No exige ser autor del post.
        """
        post = get_object_or_404(Post, pk=pk)
        obj, created = PostStar.objects.get_or_create(post=post, user=request.user)
        if not created:
            obj.delete()
            has = False
        else:
            has = True
        return Response({
            "has_starred": has,
            "stars_count": PostStar.objects.filter(post=post).count()
        })

    @action(detail=True, methods=["get"], url_path="starrers",
            permission_classes=[permissions.IsAuthenticated])
    def starrers(self, request, pk=None):
        """Devuelve listado de usuarios que dieron estrella al post."""
        post = get_object_or_404(Post, pk=pk)
        qs = post.stars.select_related("user", "user__finca_profile").order_by("-created_at")
        results = []
        for s in qs:
            try:
                fp = s.user.finca_profile
            except Exception:
                fp, _ = Profile.objects.get_or_create(user=s.user)
            results.append({
                "username": s.user.username,
                "display_name": fp.display_name or s.user.username,
                "avatar": abs_url(request, fp.avatar),
                "created_at": s.created_at,
            })
        return Response({"count": qs.count(), "results": results})

    # -------- COMENTARIOS --------
    @action(detail=True, methods=["get", "post"], url_path="comments",
            permission_classes=[permissions.IsAuthenticated])
    def comments(self, request, pk=None):
        """
        GET: devuelve árbol de comentarios (solo raíces con sus 'replies').
        POST: crea un comentario; body: { "text": "...", "parent": <id|null> }
        """
        post = get_object_or_404(Post, pk=pk)

        if request.method.lower() == "get":
            roots = (
                Comment.objects
                .filter(post=post, parent__isnull=True)
                .select_related("user", "user__finca_profile")
                .prefetch_related("replies__user", "replies__user__finca_profile", "replies__replies")
                .order_by("created_at")
            )
            data = CommentSerializer(roots, many=True, context={"request": request}).data
            return Response({"count": post.comments.count(), "results": data})

        # POST
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response({"detail": "Texto requerido."}, status=400)
        parent_id = request.data.get("parent")
        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id, post=post)

        c = Comment.objects.create(post=post, user=request.user, text=text, parent=parent)
        ser = CommentSerializer(c, context={"request": request})
        return Response({"created": ser.data, "count": post.comments.count()}, status=201)

    # -------- 📲 WHATSAPP --------
    @action(detail=True, methods=["post"], url_path="whatsapp",
            permission_classes=[permissions.IsAuthenticated])
    def whatsapp(self, request, pk=None):
        """
        Registra (idempotente) que el usuario compartió por WhatsApp.
        No se hace toggle; si ya existe no se duplica.
        """
        post = get_object_or_404(Post, pk=pk)
        PostWhatsAppShare.objects.get_or_create(post=post, user=request.user)
        return Response({
            "created": True,
            "has_shared_whatsapp": True,
            "whatsapp_count": PostWhatsAppShare.objects.filter(post=post).count(),
        })

    @action(detail=True, methods=["get"], url_path="whatsappers",
            permission_classes=[permissions.IsAuthenticated])
    def whatsappers(self, request, pk=None):
        """Devuelve el listado de usuarios que compartieron el post por WhatsApp."""
        post = get_object_or_404(Post, pk=pk)
        qs = post.whatsapp_shares.select_related("user", "user__finca_profile").order_by("-created_at")
        results = []
        for s in qs:
            try:
                fp = s.user.finca_profile
            except Exception:
                fp, _ = Profile.objects.get_or_create(user=s.user)
            results.append({
                "username": s.user.username,
                "display_name": fp.display_name or s.user.username,
                "avatar": abs_url(request, fp.avatar),
                "created_at": s.created_at,
            })
        return Response({"count": qs.count(), "results": results})

    # -------- 🔁 REPOST --------
    @action(detail=True, methods=["post"], url_path="repost",
            permission_classes=[permissions.IsAuthenticated])
    def repost(self, request, pk=None):
        """
        Crea (idempotente) un post de 'repost' del original <pk>.
        Si ya existe, devuelve el existente. Permite caption opcional en body: { "text": "..." }.
        """
        original = get_object_or_404(Post, pk=pk)
        caption = (request.data.get("text") or "").strip()
        obj, created = Post.objects.get_or_create(
            author=request.user, repost_of=original,
            defaults={"text": caption}
        )
        return Response({
            "created": created,
            "has_reposted": True,
            "reposts_count": original.reposts.count(),
            "repost": PostSerializer(obj, context={"request": request}).data,
        }, status=201 if created else 200)

    @action(detail=True, methods=["get"], url_path="reposters",
            permission_classes=[permissions.IsAuthenticated])
    def reposters(self, request, pk=None):
        """Listado de usuarios que compartieron (repost) el post <pk>."""
        post = get_object_or_404(Post, pk=pk)
        qs = post.reposts.select_related("author", "author__finca_profile").order_by("-created_at")
        results = []
        for r in qs:
            try:
                fp = r.author.finca_profile
            except Exception:
                fp, _ = Profile.objects.get_or_create(user=r.author)
            results.append({
                "username": r.author.username,
                "display_name": fp.display_name or r.author.username,
                "avatar": abs_url(request, fp.avatar),
                "created_at": r.created_at,
            })
        return Response({"count": qs.count(), "results": results})

    # -------- 🔖 GUARDADOS --------
    @action(detail=True, methods=["post"], url_path="save",
            permission_classes=[permissions.IsAuthenticated])
    def save(self, request, pk=None):
        """
        Toggle de 'guardado' para el usuario autenticado sobre el post <pk>.
        """
        post = get_object_or_404(Post, pk=pk)
        obj, created = PostSave.objects.get_or_create(post=post, user=request.user)
        if not created:
            obj.delete()
            has = False
        else:
            has = True
        return Response({
            "has_saved": has,
            "saves_count": PostSave.objects.filter(post=post).count(),
        })

    @action(detail=True, methods=["get"], url_path="savers",
            permission_classes=[permissions.IsAuthenticated])
    def savers(self, request, pk=None):
        """Listado de usuarios que guardaron el post <pk>."""
        post = get_object_or_404(Post, pk=pk)
        qs = post.saves.select_related("user", "user__finca_profile").order_by("-created_at")
        results = []
        for s in qs:
            try:
                fp = s.user.finca_profile
            except Exception:
                fp, _ = Profile.objects.get_or_create(user=s.user)
            results.append({
                "username": s.user.username,
                "display_name": fp.display_name or s.user.username,
                "avatar": abs_url(request, fp.avatar),
                "created_at": s.created_at,
            })
        return Response({"count": qs.count(), "results": results})


# ---- CommentView (eliminar) ----
class CommentViewSet(viewsets.GenericViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated, IsCommentOwnerOrPostAuthor]

    def destroy(self, request, pk=None):
        obj = get_object_or_404(Comment, pk=pk)
        self.check_object_permissions(request, obj)
        post = obj.post
        obj.delete()
        return Response({"count": post.comments.count()}, status=status.HTTP_204_NO_CONTENT)


# ========= CoverSlide (listar / guardar) =========
class CoverSlideViewSet(viewsets.ViewSet):
    """
    GET  /api/finca/cover-slides/  → lista 0..2
    POST /api/finca/cover-slides/  → reemplaza/actualiza por-slot
      - slide{n} (archivo), slide{n}_clear=1
      - slide{n}_caption, slide{n}_bibliography
      - slide{n}_text_x, slide{n}_text_y, slide{n}_color, slide{n}_font, slide{n}_text_size, slide{n}_effect
      - caption / bibliography a nivel global (fallback si no viene por-slot)
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes     = [JSONParser, MultiPartParser, FormParser]

    def list(self, request):
        qs = CoverSlide.objects.filter(user=request.user).order_by("index")
        ser = CoverSlideSerializer(qs, many=True, context={"request": request})
        first = qs.first()
        return Response({
            "results": ser.data,
            "caption": first.caption if first else "",
            "bibliography": first.bibliography if first else "",
        })

    def create(self, request):
        common_caption = (request.data.get("caption") or "").strip()
        common_biblio  = (request.data.get("bibliography") or "").strip()

        out = []
        for idx in range(3):
            f = request.FILES.get(f"slide{idx}")
            clear = request.data.get(f"slide{idx}_clear")
            # por-slot campos (opcionales)
            slot_caption = (request.data.get(f"slide{idx}_caption") or "").strip()
            slot_biblio  = (request.data.get(f"slide{idx}_bibliography") or "").strip()
            slot_text_x  = request.data.get(f"slide{idx}_text_x")
            slot_text_y  = request.data.get(f"slide{idx}_text_y")
            slot_color   = request.data.get(f"slide{idx}_color")
            slot_font    = request.data.get(f"slide{idx}_font")
            slot_size    = request.data.get(f"slide{idx}_text_size")
            slot_effect  = request.data.get(f"slide{idx}_effect")

            obj, _ = CoverSlide.objects.get_or_create(user=request.user, index=idx)

            if clear:
                if obj.image:
                    obj.image.delete(save=False)
                obj.image = None

            if f:
                obj.image = f

            # caption/bibliography por slide (con fallback global)
            if slot_caption or common_caption:
                obj.caption = slot_caption if slot_caption != "" else common_caption
            if slot_biblio or common_biblio:
                obj.bibliography = slot_biblio if slot_biblio != "" else common_biblio

            # Guardado defensivo de extras (solo si existen en el modelo)
            def _set_if_has(field, value, caster=lambda v: v):
                if value is None:
                    return
                if hasattr(obj, field):
                    try:
                        setattr(obj, field, caster(value))
                    except Exception:
                        pass

            # posiciones/estilos (si tu modelo los tiene)
            _set_if_has("text_x", slot_text_x, float)
            _set_if_has("text_y", slot_text_y, float)
            _set_if_has("text_color", slot_color, str)
            _set_if_has("text_font", slot_font, str)
            _set_if_has("text_size", slot_size, float)
            _set_if_has("effect", slot_effect, str)

            obj.save()
            out.append(obj)

        ser = CoverSlideSerializer(out, many=True, context={"request": request})
        # devolvemos también eco del caption/biblio global por conveniencia
        return Response({"results": ser.data, "caption": common_caption, "bibliography": common_biblio})
