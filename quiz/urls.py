# quiz/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('exam/<int:exam_id>/', views.take_quiz, name='take_quiz'),
    path('exam/<int:exam_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('result/<int:result_id>/review/', views.review_result, name='review_result'),
    
    # Đường dẫn dashboard của giáo viên
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/export-excel/<int:exam_id>/', views.export_exam_excel, name='export_exam_excel'),
]