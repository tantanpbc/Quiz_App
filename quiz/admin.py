from django.contrib import admin
from .models import Classroom, Exam, Question, Result

# Cấu hình hiển thị câu hỏi dạng dòng (Inline) ngay trong trang quản lý đề thi
class QuestionInline(admin.TabularInline):
    model = Question
    extra = 4  # Mặc định hiển thị sẵn 4 hàng câu hỏi trống để nhập nhanh

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    # Hiển thị các cột thông tin ngoài danh sách đề thi bao gồm trường created_at và lớp học
    list_display = ('id', 'title', 'classroom', 'duration', 'created_at')
    # Cho phép chỉnh sửa nhanh lớp học hoặc thời gian làm bài ngay ở trang danh sách
    list_editable = ('classroom', 'duration')
    search_fields = ('title',)
    
    # Tích hợp form thêm câu hỏi inline vào chung trang Add/Edit exam
    inlines = [QuestionInline]

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    filter_horizontal = ('students',)  # Tạo ô chọn hộp kép giúp quản lý danh sách học sinh cực nhanh

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'exam', 'question_text', 'correct_option')
    list_filter = ('exam',)

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'exam', 'correct_answers', 'total_questions', 'score', 'completed_at')
    list_filter = ('exam', 'student')