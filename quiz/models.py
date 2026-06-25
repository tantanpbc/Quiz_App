from django.db import models
from django.contrib.auth.models import User

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
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="exams", 
        verbose_name="Dành cho lớp"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo", null=True, blank=True)
    
    # Feature 1: Exam scheduling
    start_date = models.DateTimeField(null=True, blank=True, verbose_name="Bắt đầu vào", help_text="Để trống = mở ngay lập tức")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="Kết thúc lúc", help_text="Để trống = không có deadline")
    
    # Feature 3: Retake limits
    max_attempts = models.IntegerField(default=1, verbose_name="Số lần làm bài tối đa", help_text="1 = chỉ làm 1 lần, 0 = vô hạn")
    
    # Feature 4: Question randomization
    randomize_questions = models.BooleanField(default=False, verbose_name="Xáo trộn thứ tự câu hỏi")
    randomize_options = models.BooleanField(default=False, verbose_name="Xáo trộn thứ tự đáp án")

    def __str__(self):
        return self.title
    
    def is_available(self):
        """Check if exam is currently available for students"""
        from django.utils import timezone
        now = timezone.now()
        
        if self.start_date and now < self.start_date:
            return False, f"Đề thi chưa mở. Bắt đầu vào {self.start_date.strftime('%d/%m/%Y %H:%M')}"
        
        if self.end_date and now > self.end_date:
            return False, f"Đề thi đã đóng (kết thúc lúc {self.end_date.strftime('%d/%m/%Y %H:%M')})"
        
        return True, ""

class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField(verbose_name="Nội dung câu hỏi")
    option_a = models.CharField(max_length=200, verbose_name="Đáp án A")
    option_b = models.CharField(max_length=200, verbose_name="Đáp án B")
    option_c = models.CharField(max_length=200, verbose_name="Đáp án C")
    option_d = models.CharField(max_length=200, verbose_name="Đáp án D")
    correct_option = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')], verbose_name="Đáp án đúng")

    def __str__(self):
        return self.question_text[:50]

class Result(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    correct_answers = models.IntegerField()
    total_questions = models.IntegerField()
    score = models.FloatField()
    completed_at = models.DateTimeField(auto_now_add=True)
    answers_json = models.TextField(default="{}")
    
    # Feature 3: Track attempt number
    attempt_number = models.IntegerField(default=1, verbose_name="Lần thứ")
    
    # Feature 2: Teacher feedback on student results
    teacher_feedback = models.TextField(blank=True, verbose_name="Nhận xét của giáo viên", help_text="Nhận xét hoặc gợi ý cho học sinh")
    
    # Feature 4: Randomization seed for question order
    randomization_seed = models.IntegerField(null=True, blank=True, verbose_name="Seed xáo trộn")
    
    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.student.username} - {self.exam.title} - {self.score} (Lần {self.attempt_number})"
    
class QuizSession(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE
    )

    start_time = models.DateTimeField(
        auto_now_add=True
    )

    submitted = models.BooleanField(
        default=False
    )

    class Meta:
        unique_together = (
            'student',
            'exam'
        )

    def __str__(self):
        return f"{self.student.username} - {self.exam.title}"