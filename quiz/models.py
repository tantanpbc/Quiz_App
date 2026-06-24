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
    
    # 1. ĐÃ SỬA THÀNH on_delete CHÍNH XÁC
    classroom = models.ForeignKey(
        Classroom, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="exams", 
        verbose_name="Dành cho lớp"
    )
    
    # 2. ĐÃ BỔ SUNG TRƯỜNG NÀY ĐỂ HẾT LỖI ADMIN (E108)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo", null=True, blank=True)

    def __str__(self):
        return self.title

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

    def __str__(self):
        return f"{self.student.username} - {self.exam.title} - {self.score}"