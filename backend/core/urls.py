from django.urls import path
import core.views as views

urlpatterns = [
    path('results/<str:username>/', views.get_result)
]
