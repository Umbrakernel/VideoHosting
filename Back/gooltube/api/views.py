from rest_framework import viewsets
from .models import Video
from .serializers import VideoSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework import generics, permissions
from rest_framework.response import Response
from .serializers import RegistrationSerializer
from rest_framework import status


from rest_framework.generics import RetrieveAPIView, ListAPIView, DestroyAPIView, ListCreateAPIView # <--- ДОБАВЬТЕ ListCreateAPIView сюда
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from .models import Video, Comment
from .serializers import UserSerializer, VideoSerializer, CommentSerializer
from .permissions import IsVideoOwner

MOVIEPY_INSTALLED = False

from django.shortcuts import get_object_or_404

from django.core.files import File
import os
from django.conf import settings
import sys

MOVIEPY_INSTALLED = False

print("\n--- Debugging moviepy import ---") # Добавлено для отладки
print(f"sys.executable: {sys.executable}")
print(f"sys.path: {sys.path}")
print("Attempting to import moviepy.editor...")

try:
    from moviepy import VideoFileClip
    MOVIEPY_INSTALLED = True
    print("moviepy.editor imported successfully!")
    print("Thumbnail generation is enabled.")
except ImportError as e:
    print(f"Error importing moviepy.editor: {e}")
    print("Warning: moviepy not installed or not found in sys.path. Thumbnail generation will be skipped.")
    print("Please ensure moviepy is installed (pip install moviepy) in the correct environment.")
    print("Also ensure ffmpeg is in your system's PATH.")
except Exception as e:
    print(f"An unexpected error occurred during moviepy import: {type(e).__name__}: {e}")
    print("Warning: moviepy import failed. Thumbnail generation will be skipped.")
    print("Please ensure moviepy is installed and ffmpeg is in your system's PATH.")

print("--- End debugging moviepy import ---\n")

class CurrentUserView(RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class UserVideoListView(ListAPIView):
    serializer_class = VideoSerializer
    #permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Video.objects.filter(author=self.request.user)


class VideoViewSet(viewsets.ModelViewSet):
    queryset = Video.objects.all()
    serializer_class = VideoSerializer

    def get_permissions(self):
        """
        Определяет разрешения для каждого действия во ViewSet.
        """
        if self.action == 'list' or self.action == 'retrieve':
            permission_classes = [permissions.AllowAny]
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        elif self.action == 'destroy':
             permission_classes = [permissions.IsAuthenticated]
        elif self.action == 'user':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]

        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        instance = serializer.save(author=self.request.user)

        if MOVIEPY_INSTALLED and instance.video:
            print(f"Attempting to generate thumbnail for video {instance.pk}...")
            try:
                video_path = instance.video.path
                temp_thumbnail_path = os.path.join(settings.MEDIA_ROOT, f'temp_thumbnail_{instance.pk}.jpg')

                clip = VideoFileClip(video_path)

                frame_time = 0.5
                if clip.duration is not None and clip.duration > 0:
                    frame_time = min(frame_time, clip.duration / 2) 
                else:
                     print(f"Warning: Video {instance.pk} has zero or unknown duration. Skipping thumbnail generation.")
                     clip.close()
                     return 

                clip.save_frame(temp_thumbnail_path, t=frame_time)

                clip.close()

                with open(temp_thumbnail_path, 'rb') as f:
                    thumbnail_filename = f'thumbnail_{instance.pk}_{os.path.splitext(os.path.basename(video_path))[0]}.jpg'
                    instance.thumbnail.save(thumbnail_filename, File(f), save=True)
                    print(f"Thumbnail generated and saved for video {instance.pk}.")

                os.remove(temp_thumbnail_path)
                print(f"Temporary thumbnail file {temp_thumbnail_path} removed.")


            except Exception as e:
                print(f"Error generating thumbnail for video {instance.pk}: {e}")
                instance.thumbnail = None
                instance.save(update_fields=['thumbnail'])


        elif not MOVIEPY_INSTALLED:
             print(f"Skipping thumbnail generation for video {instance.pk}: moviepy not installed.")
        elif not instance.video:
             print(f"Skipping thumbnail generation for video {instance.pk}: no video file.")


class RegistrationAPIView(generics.GenericAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": RegistrationSerializer(user, context=self.get_serializer_context()).data,
            "message": "Пользователь успешно зарегистрирован.",
        }, status=status.HTTP_201_CREATED)
class VideoCommentsListCreateView(ListCreateAPIView):
    """
    API View для списка комментариев к видео (GET) и создания нового комментария (POST).
    GET доступен всем, POST - только авторизованным.
    """
    serializer_class = CommentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        video_id = self.kwargs['video_id']
        video = Video.objects.filter(pk=video_id).first()
        if video:
            return Comment.objects.filter(video=video)
        return Comment.objects.none()

    def perform_create(self, serializer):
         video_id = self.kwargs['video_id']
         video = Video.objects.get(pk=video_id)
         serializer.save(video=video, author=self.request.user)

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [AllowAny()]
