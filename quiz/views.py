from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from .models import Classroom, Exam, Question, Result
import json
from openpyxl import Workbook

@login_required
def home(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('teacher_dashboard')
        
    user_classrooms = request.user.classrooms.all()
    exams = Exam.objects.filter(classroom__in=user_classrooms).distinct()
    user_results = Result.objects.filter(student=request.user).select_related('exam')
    completed_exam_ids = user_results.values_list('exam_id', flat=True)

    context = {
        'exams': exams,
        'completed_exam_ids': completed_exam_ids,
        'user_results': user_results,
    }
    return render(request, 'quiz/home.html', context)

def custom_login(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('teacher_dashboard')
        return redirect('home')

    if request.method == 'POST':
        username_login = request.POST.get('username')
        password_login = request.POST.get('password')
        role = request.POST.get('role')

        user = authenticate(request, username=username_login, password=password_login)
        
        if user is not None:
            auth_login(request, user)
            if role == 'teacher' and (user.is_staff or user.is_superuser):
                return redirect('teacher_dashboard')
            elif role == 'student' and not (user.is_staff or user.is_superuser):
                return redirect('home')
            else:
                messages.error(request, "Vai trò đăng nhập chọn không khớp với quyền hạn tài khoản!")
                auth_logout(request)
                return redirect('login')
        else:
            messages.error(request, "Tài khoản hoặc mật khẩu không chính xác.")
            return redirect('login')
            
    return render(request, 'quiz/login.html')

@login_required
def take_quiz(request, exam_id):
    if request.user.is_staff or request.user.is_superuser:
        return HttpResponse("Giáo viên không được tham gia làm bài thi.", status=403)
        
    exam = get_object_or_404(Exam, id=exam_id)
    
    if exam.classroom and not exam.classroom.students.filter(id=request.user.id).exists():
        return HttpResponse("Bạn không thuộc lớp học được quyền làm đề thi này.", status=403)

    if Result.objects.filter(student=request.user, exam=exam).exists():
        messages.warning(request, "Bạn đã hoàn thành bài thi này trước đó!")
        return redirect('home')

    questions = exam.questions.all()
    context = {
        'exam': exam,
        'questions': questions,
    }
    return render(request, 'quiz/exam.html', context)

@login_required
def submit_quiz(request, exam_id):
    if request.method != 'POST':
        return redirect('home')
        
    exam = get_object_or_404(Exam, id=exam_id)
    
    if Result.objects.filter(student=request.user, exam=exam).exists():
        return HttpResponse("Bài thi này đã được nộp từ trước.", status=400)

    questions = exam.questions.all()
    correct_answers = 0
    total_questions = questions.count()
    answers_dict = {}

    for q in questions:
        selected_option = request.POST.get(f'question_{q.id}')
        answers_dict[str(q.id)] = selected_option
        
        if selected_option == q.correct_option:
            correct_answers += 1

    score = round((correct_answers / total_questions) * 10, 2) if total_questions > 0 else 0

    Result.objects.create(
        student=request.user,
        exam=exam,
        correct_answers=correct_answers,
        total_questions=total_questions,
        score=score,
        answers_json=json.dumps(answers_dict)
    )

    messages.success(request, f"Nộp bài thành công! Bạn đúng {correct_answers}/{total_questions} câu. Điểm số: {score}")
    return redirect('home')

# ========================================================
# HÀM XEM LẠI LỊCH SỬ THI VÀ ĐÁP ÁN SAI (REVIEW RESULT)
# ========================================================
@login_required
def review_result(request, result_id):
    result = get_object_or_404(Result, id=result_id)
    
    # Bảo mật: Chỉ cho phép chính học sinh làm bài hoặc Giáo viên/Admin được quyền xem lại
    if result.student != request.user and not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Bạn không có quyền xem lại kết quả bài làm này.", status=403)
        
    exam = result.exam
    questions = exam.questions.all()
    
    # Chuyển đổi dữ liệu JSON câu trả lời của học sinh thành Dict trong Python
    try:
        student_answers = json.loads(result.answers_json)
    except:
        student_answers = {}

    # Đóng gói cấu trúc dữ liệu câu hỏi đi kèm lựa chọn của học sinh để hiển thị
    questions_review = []
    for q in questions:
        # Lấy đáp án học sinh đã chọn cho câu hỏi này (nếu không chọn thì mặc định là None)
        chosen_option = student_answers.get(str(q.id))
        
        questions_review.append({
            'question_text': q.question_text,
            'option_a': q.option_a,
            'option_b': q.option_b,
            'option_c': q.option_c,
            'option_d': q.option_d,
            'correct_option': q.correct_option,
            'chosen_option': chosen_option,
            'is_correct': chosen_option == q.correct_option
        })

    context = {
        'result': result,
        'exam': exam,
        'questions_review': questions_review,
    }
    return render(request, 'quiz/review_result.html', context)

@login_required
def teacher_dashboard(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Bạn không có quyền truy cập khu vực này.", status=403)
        
    exams = Exam.objects.all().select_related('classroom').prefetch_related('questions')
    
    exams_with_results = []
    for exam in exams:
        ordered_results = Result.objects.filter(exam=exam).select_related('student').order_by('-score', 'completed_at')
        exam.ordered_results = ordered_results
        exams_with_results.append(exam)
        
    from django.contrib.auth.models import User
    context = {
        'exams_with_results': exams_with_results,
        'total_exams': Exam.objects.count(),
        'total_students': User.objects.filter(is_staff=False, is_superuser=False).count(),
        'total_results': Result.objects.count(),
    }
    return render(request, 'quiz/teacher_dashboard.html', context)

@login_required
def export_exam_excel(request, exam_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Bạn không có quyền thực hiện hành động này.", status=403)
        
    exam = get_object_or_404(Exam, id=exam_id)
    results = Result.objects.filter(exam=exam).select_related('student').order_by('-score')
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Kết quả đề thi"
    
    ws.append(["Thứ hạng", "Tài khoản học sinh", "Số câu đúng", "Tổng số câu", "Điểm số", "Thời gian nộp"])
    
    for idx, res in enumerate(results, start=1):
        ws.append([
            idx,
            res.student.username,
            res.correct_answers,
            res.total_questions,
            res.score,
            res.completed_at.strftime("%H:%M - %d/%m/%Y")
        ])
        
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="Ket_qua_{exam.id}.xlsx"'
    wb.save(response)
    return response