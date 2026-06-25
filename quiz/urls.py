from django.urls import path
from . import views

urlpatterns = [
    # Giao diện học sinh & Đăng nhập
    path('', views.home, name='home'),
    path('login/', views.custom_login, name='login'),
    path('exam/<int:exam_id>/', views.take_quiz, name='take_quiz'),
    path('exam/<int:exam_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('result/<int:result_id>/review/', views.review_result, name='review_result'),
    
    # Giáo viên Dashboard & Phân tích
    path("leaderboard/<int:exam_id>/", views.leaderboard, name="leaderboard"),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('teacher/export-excel/<int:exam_id>/', views.export_exam_excel, name='export_exam_excel'),

    # Giao diện nâng cao: Quản lý Đề thi dành cho Giáo viên
    path('teacher/exams/', views.teacher_exams, name='teacher_exams'),
    path('teacher/exam/create/', views.create_exam, name='create_exam'),
    path('teacher/exam/<int:exam_id>/edit/', views.edit_exam, name='edit_exam'),
    path('teacher/exam/<int:exam_id>/delete/', views.delete_exam, name='delete_exam'),
    path('teacher/exam/<int:exam_id>/preview/', views.exam_preview, name='exam_preview'),
    
    # Quản lý Câu hỏi
    path('teacher/exam/<int:exam_id>/questions/', views.edit_exam_questions, name='edit_exam_questions'),
    path('teacher/exam/<int:exam_id>/question/<int:question_id>/edit/', views.edit_question, name='edit_question'),
    path('teacher/exam/<int:exam_id>/question/<int:question_id>/delete/', views.delete_question, name='delete_question'),
    path('teacher/exam/<int:exam_id>/questions/reorder/', views.reorder_questions, name='reorder_questions'),
    
    # Cấu hình nhanh Preset
    path('teacher/preset/<int:preset_id>/apply/', views.apply_preset, name='apply_preset'),
]