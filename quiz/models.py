from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Classroom(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Tên lớp")
    students = models.ManyToManyField(User, blank=True, related_name="classrooms", verbose_name="Học sinh")

    def __str__(self):
        return self.name

class Exam(models.Model):
    title = models.CharField(max_length=200, verbose_name="Tên đề thi")
    duration = models.IntegerField(verbose_name="Thời gian (phút)")
    
    classroom = models.ForeignKey(
        Classroom, 
        on_delete=models.SET_NULL, \
        null=True, \
        blank=True, \
        related_name="exams", \
        verbose_name="Dành cho lớp"
    )
    
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_exams", verbose_name="Giáo viên")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo", null=True, blank=True)
    
    # Feature: Exam scheduling
    start_date = models.DateTimeField(null=True, blank=True, verbose_name="Bắt đầu vào", help_text="Để trống = mở ngay lập tức")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="Kết thúc lúc", help_text="Để trống = không có deadline")
    
    # Advanced Time Constraints
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả đề thi")
    show_timer = models.BooleanField(default=True, verbose_name="Hiển thị bộ đếm thời gian")
    time_warning_minutes = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(60)],
        verbose_name="Cảnh báo thời gian còn lại (phút)"
    )
    
    # Question & Scoring Settings
    passing_percentage = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Phần trăm đạt yêu cầu (%)",
        help_text="Học sinh cần bao nhiêu % để đạt điểm qua"
    )
    
    show_score = models.BooleanField(default=True, verbose_name="Hiển thị điểm số cho học sinh")
    show_correct_answers = models.BooleanField(default=True, verbose_name="Hiển thị đáp án đúng sau khi nộp")
    
    # Review Settings
    allow_review = models.BooleanField(
        default=True,
        verbose_name="Cho phép học sinh xem lại bài làm sau nộp"
    )
    
    # Shuffle Options
    randomize_questions = models.BooleanField(default=False, verbose_name="Xáo trộn câu hỏi")
    randomize_options = models.BooleanField(default=False, verbose_name="Xáo trộn các lựa chọn đáp án")
    
    # Access Rules
    max_attempts = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="Số lượt làm bài tối đa"
    )
    password_protect = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Mật khẩu vào thi",
        help_text="Để trống nếu công khai"
    )
    
    # Status
    is_published = models.BooleanField(default=True, verbose_name="Công khai đề thi ngay")

    def __str__(self):
        return self.title

    def get_duration_display(self):
        if self.duration >= 60:
            hours = self.duration // 60
            mins = self.duration % 60
            return f"{hours}h {mins}m" if mins else f"{hours}h"
        return f"{self.duration} phút"

    def is_available(self):
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False, f"Đề thi chưa mở. Sẽ mở vào lúc {self.start_date.strftime('%H:%M %d/%m/%Y')}."
        if self.end_date and now > self.end_date:
            return False, f"Đề thi đã đóng vào lúc {self.end_date.strftime('%H:%M %d/%m/%Y')}."
        return True, ""

class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField(verbose_name="Câu hỏi")
    option_a = models.CharField(max_length=200, verbose_name="Đáp án A")
    option_b = models.CharField(max_length=200, verbose_name="Đáp án B")
    option_c = models.CharField(max_length=200, verbose_name="Đáp án C")
    option_d = models.CharField(max_length=200, verbose_name="Đáp án D")
    correct_option = models.CharField(
        max_length=1, 
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')],
        verbose_name="Đáp án đúng"
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Thứ tự câu hỏi")

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.exam.title} - {self.question_text[:30]}"

class Result(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    correct_answers = models.IntegerField()
    total_questions = models.IntegerField()
    score = models.FloatField()
    answers_json = models.TextField(default="{}")
    completed_at = models.DateTimeField(auto_now_add=True)

    attempt_number = models.PositiveIntegerField(default=1, verbose_name="Lượt làm bài số")
    randomization_seed = models.IntegerField(blank=True, null=True, verbose_name="Hạt giống xáo trộn")

    def __str__(self):
        return f"{self.student.username} - {self.exam.title} - {self.score}"

class QuizSession(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

class ExamConstraintPreset(models.Model):
    name = models.CharField(max_length=100, verbose_name="Tên mẫu cấu hình")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả mẫu")
    default_duration = models.PositiveIntegerField(default=60, verbose_name="Thời gian mặc định (phút)")
    default_max_attempts = models.PositiveIntegerField(default=1, verbose_name="Số lượt làm mặc định")
    default_passing_percentage = models.PositiveIntegerField(default=50, verbose_name="Phần trăm đạt mặc định")
    default_show_timer = models.BooleanField(default=True, verbose_name="Bật bộ đếm thời gian")
    default_show_score = models.BooleanField(default=True, verbose_name="Hiện điểm")
    default_show_correct_answers = models.BooleanField(default=True, verbose_name="Hiện đáp án đúng")
    default_allow_review = models.BooleanField(default=True, verbose_name="Cho phép xem lại")

    class Meta:
        verbose_name = "Mẫu cấu hình sẵn"
        verbose_name_plural = "Các mẫu cấu hình sẵn"

    def __str__(self):
        return self.name

class ExamGradeRule(models.Model):
    exam = models.OneToOneField('Exam', on_delete=models.CASCADE, related_name='grade_rule')
    grade_a_min = models.IntegerField(default=90, verbose_name="Điểm A tối thiểu (%)")
    grade_b_min = models.IntegerField(default=80, verbose_name="Điểm B tối thiểu (%)")
    grade_c_min = models.IntegerField(default=70, verbose_name="Điểm C tối thiểu (%)")
    grade_d_min = models.IntegerField(default=60, verbose_name="Điểm D tối thiểu (%)")
    grade_f_min = models.IntegerField(default=0, verbose_name="Điểm F tối thiểu (%)")
    
    class Meta:
        verbose_name = "Quy tắc chấm điểm"
    
    def __str__(self):
        return f"Quy tắc chấm cho {self.exam.title}"

class ExamQuestionPool(models.Model):
    exam = models.OneToOneField('Exam', on_delete=models.CASCADE, related_name='question_pool')
    total_questions_in_pool = models.IntegerField(verbose_name="Tổng câu hỏi trong pool")
    questions_to_select = models.IntegerField(verbose_name="Số câu hỏi để chọn ngẫu nhiên")
    use_pool = models.BooleanField(default=False, verbose_name="Sử dụng pool ngẫu nhiên")