# finca/urls.py
from django.urls import path
from .views import (
    MyFincaViewSet, PostViewSet, CommentViewSet, CoverSlideViewSet
)

finca_view        = MyFincaViewSet.as_view({"get": "list", "put": "update", "post": "create"})
post_view         = PostViewSet.as_view({"get": "list", "post": "create"})
post_detail       = PostViewSet.as_view({"patch": "partial_update", "delete": "destroy"})
post_feed         = PostViewSet.as_view({"get": "feed"})
post_saved        = PostViewSet.as_view({"get": "saved"})             # 🔖
post_star         = PostViewSet.as_view({"post": "star"})
post_starrers     = PostViewSet.as_view({"get": "starrers"})
post_comments     = PostViewSet.as_view({"get": "comments", "post": "comments"})
post_whatsapp     = PostViewSet.as_view({"post": "whatsapp"})
post_whatsappers  = PostViewSet.as_view({"get": "whatsappers"})
post_repost       = PostViewSet.as_view({"post": "repost"})
post_reposters    = PostViewSet.as_view({"get": "reposters"})
post_save         = PostViewSet.as_view({"post": "save"})             # 🔖
post_savers       = PostViewSet.as_view({"get": "savers"})            # 🔖

# borrar comentario (autor del comentario o autor del post)
comment_detail    = CommentViewSet.as_view({"delete": "destroy"})

# slides de portada
cover_slides      = CoverSlideViewSet.as_view({"get": "list", "post": "create"})

urlpatterns = [
    path("",                           finca_view,        name="mi-finca"),
    path("posts/",                     post_view,         name="finca-posts"),
    path("posts/<int:pk>/",            post_detail,       name="finca-post-detail"),
    path("feed/",                      post_feed,         name="finca-feed"),
    path("saved/",                     post_saved,        name="finca-saved"),
    path("posts/<int:pk>/star/",       post_star,         name="finca-post-star"),
    path("posts/<int:pk>/starrers/",   post_starrers,     name="finca-post-starrers"),
    path("posts/<int:pk>/comments/",   post_comments,     name="finca-post-comments"),
    path("posts/<int:pk>/whatsapp/",   post_whatsapp,     name="finca-post-whatsapp"),
    path("posts/<int:pk>/whatsappers/",post_whatsappers,  name="finca-post-whatsappers"),
    path("posts/<int:pk>/repost/",     post_repost,       name="finca-post-repost"),
    path("posts/<int:pk>/reposters/",  post_reposters,    name="finca-post-reposters"),
    path("posts/<int:pk>/save/",       post_save,         name="finca-post-save"),
    path("posts/<int:pk>/savers/",     post_savers,       name="finca-post-savers"),

    # eliminar comentario
    path("comments/<int:pk>/",         comment_detail,    name="finca-comment-detail"),

    # slides de portada
    path("cover-slides/",              cover_slides,      name="finca-cover-slides"),
]
