from django.shortcuts import render
from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404

from .models import *
from .serializers import *
from .permissions import IsOwnerOrReadOnly

from django.conf import settings
import os
# Create your views here.
class PostViewSet(viewsets.GenericViewSet,
    mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, mixins.UpdateModelMixin):
    queryset = Post.objects.all()
    # serializer_class = PostSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        return PostSerializer
    
    def get_permissions(self):
        if self.action in ["create","update","destroy","partial_update"]:
            return [IsAdminUser()]
        return []

    def create(self, request):
        serializer = self.get_serializer(data =  request.data)
        serializer.is_valid(raise_exception = True)
        self.perform_create(serializer)

        post = serializer.instance
        self.handle_tags(post)

        if 'image' in request.FILES:
            post.image = request.FILES['image']
            post.save()

        return Response(serializer.data)

    def perform_update(self, serializer):
        post = serializer.save()
        post.tag.clear()

        self.handle_tags(post)

    def handle_tags(self, post):
        words = post.content.split(' ')
        tag_list = []
        for w in words:
            if w[0]=='#':
                tag_list.append(w[1:])

        for t in tag_list:
            tag, created = Tag.objects.get_or_create(name = t)
            post.tag.add(tag)

        post.save()

    @action(methods=["GET"],detail=False)
    def recommend(self, request):
        recommended_post = self.get_queryset().order_by("-like_cnt")[:3]
        recommended_post_serializer = PostListSerializer(recommended_post, many = True)
        return Response(recommended_post_serializer.data)
    
    @action(methods=['GET'],detail=True)
    def like(self, request, pk = None):
        liked_post = self.get_object()
        user = request.user
        if user in liked_post.like.all():
            liked_post.like.remove(user)
            liked_post.like_cnt -= 1
        else:
            liked_post.like.add(user)
            liked_post.like_cnt += 1

        liked_post.save(update_fields=["like_cnt"])
        return Response()

class CommentViewSet(viewsets.GenericViewSet,
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin):
    queryset = Comment.objects.all()
    serializer_class =  CommentSerializer

    def get_permissions(self):
        if self.action in ["create","update","destroy","partial_update"]:
            return [IsOwnerOrReadOnly()]
        return []
    
    def get_object(self):
        obj = super().get_object()
        return obj


class PostCommentViewSet(viewsets.GenericViewSet,
    mixins.ListModelMixin, mixins.CreateModelMixin):
    # queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    # def list(self, request, post_id = None):
    #     post = get_object_or_404(Post, id = post_id)
    #     queryset = self.filter_queryset(self.get_queryset().filter(post=post))
    #     serializer = self.get_serializer(queryset, many = True)
    #     return Response(serializer.data)

    def get_queryset(self):
        post = self.kwargs.get("post_id")
        queryset = Comment.objects.filter(post_id = post)
        return queryset


    def create(self, request, post_id = None):
        post = get_object_or_404(Post, id = post_id)
        serializer = self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(post=post)
        return Response(serializer.data)
    
class TagViewSet(viewsets.GenericViewSet,
    mixins.RetrieveModelMixin):
    queryset =  Tag.objects.all()
    serializer_class = TagSerializer
    lookup_field = "name"
    lookup_url_kwarg = "tag_name"

    def retrieve(self, request, *args, **kwargs):
        tag_name = kwargs.get("tag_name")
        tag = get_object_or_404(Tag, name = tag_name)
        posts = Post.objects.filter(tag = tag)
        serializer = PostSerializer(posts, many =True)

        return Response(serializer.data)