from django.contrib import admin
from .models import Classroom, Exam, Question, Result

# Cấu hình hiển thị câu hỏi dạng dòng (Inline) ngay trong trang quản lý đề thi
class QuestionInline(admin.TabularInline):
    model = Question
    extra = 4  # Mặc định hiển thị sẵn 4 hàng câu hỏi trống để nhập nhanh

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'classroom', 'duration', 'max_attempts', 'status_badge', 'created_at')
    list_editable = ('classroom', 'duration', 'max_attempts')
    search_fields = ('title',)
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('title', 'duration', 'classroom', 'created_at')
        }),
        ('Lịch trình & Khả dụng', {
            'fields': ('start_date', 'end_date'),
            'description': 'Để trống = không giới hạn thời gian'
        }),
        ('Giới hạn & Xáo trộn', {
            'fields': ('max_attempts', 'randomize_questions', 'randomize_options'),
            'description': '• max_attempts = 0 để cho phép làm vô hạn<br/>• Bật xáo trộn để chống gian lận'
        }),
    )
    
    inlines = [QuestionInline]
    
    def status_badge(self, obj):
        """Show exam availability status"""
        is_available, msg = obj.is_available()
        if is_available:
            return "✅ Mở"
        return "🔒 Đóng"
    status_badge.short_description = "Trạng thái"

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
    list_display = ('id', 'student', 'exam', 'correct_answers', 'total_questions', 'score', 'attempt_number', 'completed_at')
    list_filter = ('exam', 'student', 'attempt_number')
    search_fields = ('student__username', 'exam__title')
    
    fields = ('student', 'exam', 'correct_answers', 'total_questions', 'score', 'attempt_number', 'completed_at', 'answers_json', 'teacher_feedback', 'randomization_seed')
    readonly_fields = ('student', 'exam', 'correct_answers', 'total_questions', 'score', 'completed_at', 'answers_json', 'attempt_number', 'randomization_seed')
    
    def has_add_permission(self, request):
        return False  # Results created by submit_quiz, not manually