from rest_framework import serializers
from .models import *

class CommentSerializer(serializers.ModelSerializer):
    
    post = serializers.SerializerMethodField()
    def get_post(self, instance):
        return instance.post.title
    
    class Meta:
        model = Comment
        fields = '__all__'
        read_only_fields = ['id','post']

class PostSerializer(serializers.ModelSerializer):

    comments = serializers.SerializerMethodField()
    tag = serializers.SerializerMethodField()
    image =  serializers.ImageField(use_url = True, required = False)
    like_cnt = serializers.IntegerField()
    dislike_cnt = serializers.IntegerField()


    def get_comments(self, instance):
        serializer = CommentSerializer(instance.comments, many = True)
        return serializer.data
    
    def get_tag(self, instance):
        tags = instance.tag.all()
        return [tag.name for tag in tags]

    class Meta:
        model = Post
        # exclude = ('like_cnt','like')
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at','comments','like_cnt']
        

class PostListSerializer(serializers.ModelSerializer):
    comments_cnt =  serializers.SerializerMethodField()
    tag = serializers.SerializerMethodField()
    image =  serializers.ImageField(use_url = True, required = False)
    like_cnt = serializers.IntegerField()
    dislike_cnt = serializers.IntegerField()

    def get_comments_cnt(self, instance):
        return instance.comments.count()
    
    def get_tag(self, instance):
        tags = instance.tag.all()
        return [tag.name for tag in tags]
    

    class Meta:
        model = Post
        fields = ['id','title','writer','created_at','updated_at','comments_cnt','tag','image','like_cnt','dislike_cnt']
        read_only_field = ['id', 'created_at', 'updated_at','comments_cnt','like_cnt','dislike_cnt']

class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = '__all__'