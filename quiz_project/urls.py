# quiz_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from quiz import views as quiz_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Định tuyến sang hàm login phân vai trò mới viết
    path('login/', quiz_views.custom_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    path('', include('quiz.urls')), 
]