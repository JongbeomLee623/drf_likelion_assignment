from django.shortcuts import render
from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404

from .paginations import *
from .models import *
from .serializers import *
from .permissions import IsOwnerOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.conf import settings
from django.db.models import Q, Count
import os
# Create your views here.
class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.annotate(
        like_cnt = Count(
            "reactions", filter = Q(reactions__reaction= "like"), distinct = True
            ),
        dislike_cnt = Count(
            "reactions", filter = Q(reactions__reaction= "dislike"), distinct = True
        ),
    )
    # serializer_class = PostSerializer
    filter_backends =[DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    filterset_fields = ["title", "writer", "tag__name"]
    search_fields = ["title", "writer", "=tag__name"]
    ordering_fields = ["created_at", "updated_at", "like_cnt", "dislike_cnt"]

    pagination_class = PostPagination

    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        return PostSerializer
    
    def get_permissions(self):
        if self.action in ["create","update","destroy","partial_update"]:
            return [IsAdminUser()]
        elif self.action in ["likes"]:
            return [IsAuthenticated()]
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
    
    @action(methods=["POST"], detail= True, permission_classes = [IsAuthenticated])
    def likes(self, request, pk=None):
        post = self.get_object()
        reaction = PostReaction.objects.filter(post=post, user=request.user).first()
        if reaction:
            if reaction.reaction == "like":
                reaction.delete()
            else:
                reaction.reaction = "like"
                reaction.save()
        else:
            PostReaction.objects.create(post=post, user=request.user, reaction="like")
        return Response()
    
    @action(methods=["POST"], detail= True, permission_classes = [IsAuthenticated])
    def dislikes(self, request, pk=None):
        post = self.get_object()
        reaction = PostReaction.objects.filter(post=post, user=request.user).first()
        if reaction:
            if reaction.reaction == "dislike":
                reaction.delete()
            else:
                reaction.reaction = "dislike"
                reaction.save()
        else:
            PostReaction.objects.create(post=post, user=request.user, reaction="dislike")
        return Response()
    
    @action(methods=["GET"], detail= False)
    def top5(self, request):
        queryset = self.get_queryset().order_by("-like_cnt")[:5]
        serializer = PostListSerializer(queryset, many = True)
        return Response(serializer.data)


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