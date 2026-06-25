from django import forms
from django.utils import timezone
from .models import Exam, Question, Classroom, ExamConstraintPreset
from datetime import timedelta


class ExamCreationForm(forms.ModelForm):
    """
    Main form for teachers to create/edit exams with all constraints
    Matches the existing Exam model structure
    """
    
    # Basic Info
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none',
            'placeholder': 'Ví dụ: Kiểm tra Chương 1 - Toán 10'
        }),
        label='Tên đề thi'
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none',
            'rows': 3,
            'placeholder': 'Mô tả, hướng dẫn cho học sinh (tùy chọn)'
        }),
        label='Mô tả đề thi'
    )
    
    # Time Settings
    duration = forms.IntegerField(
        min_value=1,
        max_value=480,
        initial=60,
        widget=forms.NumberInput(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none',
            'placeholder': '60'
        }),
        label='Thời gian làm bài (phút)',
        help_text='Tối thiểu 1 phút, tối đa 480 phút (8 giờ)'
    )
    
    show_timer = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-slate-700 accent-indigo-500'
        }),
        label='Hiển thị bộ đếm thời gian cho học sinh'
    )
    
    time_warning_minutes = forms.IntegerField(
        min_value=1,
        max_value=60,
        initial=5,
        widget=forms.NumberInput(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none',
            'placeholder': '5'
        }),
        label='Cảnh báo còn lại (phút)',
        help_text='Hiển thị cảnh báo khi còn lại bao nhiêu phút'
    )
    
    # Attempt Settings
    max_attempts = forms.IntegerField(
        min_value=0,
        max_value=100,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none',
            'placeholder': '1'
        }),
        label='Số lần làm bài tối đa',
        help_text='0 = vô hạn, 1 = chỉ làm 1 lần'
    )
    
    allow_review = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-slate-700 accent-indigo-500'
        }),
        label='Cho phép học sinh xem lại bài làm sau nộp'
    )
    
    # Question & Scoring
    passing_percentage = forms.IntegerField(
        min_value=0,
        max_value=100,
        initial=50,
        widget=forms.NumberInput(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none',
            'placeholder': '50'
        }),
        label='Phần trăm đạt yêu cầu (%)',
        help_text='Học sinh cần bao nhiêu phần trăm để đạt'
    )
    
    show_score = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-slate-700 accent-indigo-500'
        }),
        label='Hiển thị điểm số cho học sinh'
    )
    
    show_correct_answers = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-slate-700 accent-indigo-500'
        }),
        label='Hiển thị đáp án đúng sau khi nộp'
    )
    
    # Randomization
    randomize_questions = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-slate-700 accent-indigo-500'
        }),
        label='Xáo trộn thứ tự câu hỏi'
    )
    
    randomize_options = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-slate-700 accent-indigo-500'
        }),
        label='Xáo trộn thứ tự đáp án'
    )
    
    # Difficulty
    difficulty_level = forms.ChoiceField(
        choices=[
            ('easy', '⭐ Dễ'),
            ('medium', '⭐⭐ Trung bình'),
            ('hard', '⭐⭐⭐ Khó'),
        ],
        initial='medium',
        widget=forms.Select(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none'
        }),
        label='Mức độ khó'
    )
    
    # Classroom
    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(),
        required=False,
        empty_label="-- Công khai cho tất cả học sinh --",
        widget=forms.Select(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none'
        }),
        label='Dành cho lớp học'
    )
    
    # Schedule
    start_date = forms.DateTimeField(
        required=False,
        initial=timezone.now,
        widget=forms.DateTimeInput(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none',
            'type': 'datetime-local'
        }),
        label='Ngày giờ mở đề thi',
        help_text='Để trống = mở ngay lập tức'
    )
    
    end_date = forms.DateTimeField(
        required=False,
        initial=timezone.now() + timedelta(days=7),
        widget=forms.DateTimeInput(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none',
            'type': 'datetime-local'
        }),
        label='Ngày giờ đóng đề thi',
        help_text='Để trống = không có deadline'
    )
    
    # Public/Private
    is_public = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-slate-700 accent-indigo-500'
        }),
        label='Công khai (tất cả học sinh có thể xem)',
        help_text='Nếu không chọn, chỉ học sinh trong lớp mới có quyền'
    )
    
    class Meta:
        model = Exam
        fields = [
            'title', 'description', 'classroom',
            'duration', 'show_timer', 'time_warning_minutes',
            'max_attempts', 'allow_review',
            'passing_percentage', 'show_score', 'show_correct_answers',
            'randomize_questions', 'randomize_options',
            'difficulty_level',
            'start_date', 'end_date',
            'is_public'
        ]


class QuestionForm(forms.ModelForm):
    """Form for adding/editing questions in an exam"""
    
    question_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none',
            'rows': 3,
            'placeholder': 'Nhập nội dung câu hỏi...'
        }),
        label='Nội dung câu hỏi'
    )
    
    option_a = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none',
            'placeholder': 'Đáp án A'
        }),
        label='Đáp án A'
    )
    
    option_b = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none',
            'placeholder': 'Đáp án B'
        }),
        label='Đáp án B'
    )
    
    option_c = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none',
            'placeholder': 'Đáp án C'
        }),
        label='Đáp án C'
    )
    
    option_d = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none',
            'placeholder': 'Đáp án D'
        }),
        label='Đáp án D'
    )
    
    correct_option = forms.ChoiceField(
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')],
        widget=forms.Select(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none'
        }),
        label='Đáp án đúng'
    )
    
    class Meta:
        model = Question
        fields = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option']


class ExamQuickSetupForm(forms.Form):
    """
    Quick setup form using presets
    Lets teachers quickly create exams using predefined templates
    """
    preset = forms.ModelChoiceField(
        queryset=ExamConstraintPreset.objects.all(),
        empty_label="-- Chọn mẫu cấu hình --",
        widget=forms.Select(attrs={
            'class': 'w-full bg-slate-950 border border-slate-700 rounded-lg py-2 px-3 text-white focus:border-indigo-500 focus:outline-none'
        }),
        label='Chọn mẫu cấu hình nhanh',
        help_text='Sử dụng cấu hình mẫu để tiết kiệm thời gian'
    )
    
    use_preset_settings = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded border-slate-700 accent-indigo-500'
        }),
        label='Áp dụng tất cả cài đặt từ mẫu'
    )
