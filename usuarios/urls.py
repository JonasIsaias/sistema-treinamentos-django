from django.urls import path, include
from . import views

urlpatterns = [
    path('', include('core.urls')),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
]