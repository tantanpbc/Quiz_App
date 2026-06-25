from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Avg, Max, Min, Count, Q
from .models import Classroom, Exam, Question, Result, QuizSession, ExamConstraintPreset
from .forms import ExamCreationForm, QuestionForm, ExamQuickSetupForm
import json
from openpyxl import Workbook
from django.utils import timezone
from datetime import timedelta

@login_required
def home(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('teacher_dashboard')

    user_classrooms = request.user.classrooms.all()
    exams = Exam.objects.filter(classroom__in=user_classrooms).distinct()

    user_results = Result.objects.filter(student=request.user).select_related('exam').order_by('-completed_at')
    completed_exam_ids = user_results.values_list('exam_id', flat=True)

    for exam in exams:
        exam.student_attempts = Result.objects.filter(student=request.user, exam=exam).count()
        # Tính toán trạng thái khả dụng của đề thi
        is_avail, msg = exam.is_available()
        exam.is_available_status = is_avail
        exam.available_message = msg

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
    # 1. Kiểm tra phân quyền: Không cho phép Giáo viên/Admin tham gia làm bài
    if request.user.is_staff or request.user.is_superuser:
        return HttpResponse("Giáo viên không được tham gia làm bài thi.", status=403)
        
    exam = get_object_or_404(Exam, id=exam_id)
    
    # 2. Kiểm tra phân quyền: Thí sinh phải thuộc lớp được gán đề
    if exam.classroom and not exam.classroom.students.filter(id=request.user.id).exists():
        return HttpResponse("Bạn không thuộc lớp học được quyền làm đề thi này.", status=403)

    # 3. Kiểm tra số lượt làm bài thực tế của học sinh
    attempts_count = Result.objects.filter(student=request.user, exam=exam).count()
    if attempts_count >= exam.max_attempts:
        messages.warning(request, f"Bạn đã dùng hết số lượt làm bài cho phép ({exam.max_attempts} lượt)!")
        return redirect('home')

    # 4. TÍNH TOÁN SỐ LƯỢT LÀM BÀI CÒN LẠI (Sửa lỗi mất thông tin lượt làm)
    remaining_attempts = exam.max_attempts - attempts_count

    # 5. QUẢN LÝ THỜI GIAN LÀM BÀI QUA SESSIONS (Sửa lỗi đồng hồ --:--)
    # Tìm xem học sinh có phiên làm bài nào chưa hoàn thành cho đề này không, nếu không thì tạo mới
    session, created = QuizSession.objects.get_or_create(
        student=request.user,
        exam=exam,
        is_completed=False,
        defaults={'started_at': timezone.now()}
    )
    
    # Tính số giây đã trôi qua kể từ khi bắt đầu phiên làm bài
    elapsed_seconds = (timezone.now() - session.started_at).total_seconds()
    total_exam_seconds = exam.duration * 60
    remaining_seconds = int(total_exam_seconds - elapsed_seconds)
    
    # Phòng trường hợp thời gian bị âm khi học sinh tải lại trang lúc sát giờ hết
    if remaining_seconds < 0:
        remaining_seconds = 0

    # 6. Xử lý câu hỏi (Xáo trộn nếu có cấu hình)
    questions = exam.questions.all()
    if exam.randomize_questions:
        questions = questions.order_by('?')

    # 7. TRUYỀN ĐẦY ĐỦ CÁC THAM SỐ CẦN THIẾT SANG TEMPLATE
    context = {
        'exam': exam,
        'questions': questions,
        'remaining_attempts': remaining_attempts,  # Truyền số lượt còn lại hiển thị ở khối màu vàng
        'remaining_seconds': remaining_seconds,    # Truyền số giây cho JavaScript bắt đầu đếm lùi
    }
    
    # Lưu ý: Chỉnh sửa lại tên file template ở đây cho đúng với file bạn đang dùng 
    # (Nếu file của bạn đặt tên là 'quiz/take_quiz.html' thay vì 'quiz/exam.html')
    return render(request, 'quiz/exam.html', context)

@login_required
def submit_quiz(request, exam_id):
    if request.method != 'POST':
        return redirect('home')
        
    exam = get_object_or_404(Exam, id=exam_id)
    
    attempts_count = Result.objects.filter(student=request.user, exam=exam).count()
    if attempts_count >= exam.max_attempts:
        return HttpResponse("Bạn đã hết lượt làm bài thi này.", status=400)

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

    result = Result.objects.create(
        student=request.user,
        exam=exam,
        correct_answers=correct_answers,
        total_questions=total_questions,
        score=score,
        answers_json=json.dumps(answers_dict)
    )

    messages.success(request, f"Nộp bài thành công! Điểm số: {score}")
    return render(request, 'quiz/result.html', {'result': result})

@login_required
def review_result(request, result_id):
    result = get_object_or_404(Result, id=result_id)
    if result.student != request.user and not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Bạn không có quyền xem lại kết quả bài làm này.", status=403)
        
    exam = result.exam
    if not exam.allow_review and not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Đề thi này không cho phép xem lại đáp án.", status=403)

    questions = exam.questions.all()
    try:
        student_answers = json.loads(result.answers_json)
    except:
        student_answers = {}

    questions_review = []
    for q in questions:
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
def analytics_dashboard(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Không có quyền truy cập", status=403)
    return render(request, 'quiz/analytics.html')

@login_required
def leaderboard(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    return render(request, 'quiz/leaderboard.html', {'exam': exam})

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
            idx, res.student.username, res.correct_answers,
            res.total_questions, res.score, res.completed_at.strftime("%H:%M - %d/%m/%Y")
        ])
        
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="Ket_qua_{exam.id}.xlsx"'
    wb.save(response)
    return response

# ================== NEW TEACHER EXAM MANAGEMENT VIEWS ==================

@login_required
def teacher_exams(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Bạn không có quyền.", status=403)
    exams = Exam.objects.all().order_by('-created_at')
    return render(request, 'quiz/teacher_exams.html', {'exams': exams})

@login_required
@require_http_methods(["GET", "POST"])
def create_exam(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Bạn không có quyền tạo đề thi.", status=403)
    
    if request.method == 'POST':
        form = ExamCreationForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.teacher = request.user
            exam.save()
            messages.success(request, f"✅ Tạo đề thi '{exam.title}' thành công! Hãy thêm câu hỏi.")
            return redirect('edit_exam_questions', exam_id=exam.id)
    else:
        form = ExamCreationForm()
    
    presets = ExamConstraintPreset.objects.all()
    preset_form = ExamQuickSetupForm()
    
    return render(request, 'quiz/create_exam.html', {
        'form': form,
        'preset_form': preset_form,
        'presets': presets,
        'is_edit': False,
        'page_title': 'Tạo Đề Thi Mới',
        'page_icon': 'plus-circle'
    })

@login_required
@require_http_methods(["GET", "POST"])
def edit_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Bạn không có quyền.", status=403)
        
    if request.method == 'POST':
        form = ExamCreationForm(request.POST, instance=exam)
        if form.is_valid():
            form.save()
            messages.success(request, f"✅ Cập nhật cài đặt đề thi '{exam.title}' thành công!")
            return redirect('teacher_exams')
    else:
        form = ExamCreationForm(instance=exam)
        
    return render(request, 'quiz/create_exam.html', {
        'form': form,
        'exam': exam,
        'is_edit': True,
        'page_title': 'Chỉnh Sửa Cài Đặt Đề Thi',
        'page_icon': 'cog'
    })

@login_required
@require_http_methods(["POST"])
def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Bạn không có quyền.", status=403)
    title = exam.title
    exam.delete()
    messages.success(request, f"🗑️ Đã xóa đề thi '{title}' và tất cả các câu hỏi liên quan.")
    return redirect('teacher_exams')

@login_required
@require_http_methods(["GET", "POST"])
def edit_exam_questions(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Bạn không có quyền.", status=403)
        
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.exam = exam
            # Đặt số thứ tự cuối cùng
            max_order = exam.questions.aggregate(Max('order'))['order__max']
            question.order = (max_order or 0) + 1
            question.save()
            messages.success(request, "✅ Đã thêm câu hỏi mới thành công!")
            return redirect('edit_exam_questions', exam_id=exam.id)
    else:
        form = QuestionForm()
        
    questions = exam.questions.all().order_by('order')
    return render(request, 'quiz/edit_exam_questions.html', {
        'exam': exam,
        'questions': questions,
        'form': form,
        'total_questions': questions.count()
    })

@login_required
@require_http_methods(["GET", "POST"])
def edit_question(request, exam_id, question_id):
    exam = get_object_or_404(Exam, id=exam_id)
    question = get_object_or_404(Question, id=question_id, exam=exam)
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Bạn không có quyền.", status=403)
        
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Cập nhật câu hỏi thành công!")
            return redirect('edit_exam_questions', exam_id=exam.id)
    else:
        form = QuestionForm(instance=question)
        
    return render(request, 'quiz/edit_exam_questions.html', {
        'exam': exam,
        'form': form,
        'editing_question': question,
        'questions': exam.questions.all().order_by('order'),
        'total_questions': exam.questions.count()
    })

@login_required
@require_http_methods(["POST"])
def delete_question(request, exam_id, question_id):
    exam = get_object_or_404(Exam, id=exam_id)
    question = get_object_or_404(Question, id=question_id, exam=exam)
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Bạn không có quyền.", status=403)
    question.delete()
    messages.success(request, "🗑️ Đã xóa câu hỏi.")
    return redirect('edit_exam_questions', exam_id=exam.id)

@login_required
@require_http_methods(["POST"])
def reorder_questions(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    try:
        data = json.loads(request.body)
        question_ids = data.get('question_ids', [])
        with transaction.atomic():
            for index, q_id in enumerate(question_ids):
                Question.objects.filter(id=q_id, exam=exam).update(order=index)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def apply_preset(request, preset_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    try:
        preset = ExamConstraintPreset.objects.get(id=preset_id)
        return JsonResponse({
            'status': 'success',
            'preset': {
                'duration': preset.default_duration,
                'max_attempts': preset.default_max_attempts,
                'passing_percentage': preset.default_passing_percentage,
                'show_timer': preset.default_show_timer,
                'show_score': preset.default_show_score,
                'show_correct_answers': preset.default_show_correct_answers,
                'allow_review': preset.default_allow_review,
            }
        })
    except ExamConstraintPreset.DoesNotExist:
        return JsonResponse({'error': 'Preset not found'}, status=404)

@login_required
def exam_preview(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponse("Bạn không có quyền xem.", status=403)
    
    now = timezone.now()
    if exam.start_date:
        if now < exam.start_date:
            status, status_color = "⏰ Chưa mở", "yellow"
        elif exam.end_date and now > exam.end_date:
            status, status_color = "🔒 Đã đóng", "red"
        else:
            status, status_color = "✅ Đang mở", "green"
    else:
        status, status_color = "✅ Đang mở", "green"
    
    context = {
        'exam': exam,
        'status': status,
        'status_color': status_color,
        'total_questions': exam.questions.count(),
        'page_title': 'Xem Trước Thiết Lập Đề Thi'
    }
    return render(request, 'quiz/exam_preview.html', context)