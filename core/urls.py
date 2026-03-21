from django.contrib import admin
from django.urls import path
from detector.views import game_case, index

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('api/game-case/', game_case, name='game_case'),
]
