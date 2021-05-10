from django.urls import path
import core.views as views

urlpatterns = [
    path('user/<str:username>/', views.get_userinfo),
    path('match/<str:username>/', views.get_matchinfo)
]
