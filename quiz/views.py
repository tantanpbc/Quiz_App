from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from .models import Classroom, Exam, Question, Result
from django.db.models import Avg, Max, Min, Count, Q
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

    # Feature 1: Check exam availability (scheduling)
    is_available, unavailable_msg = exam.is_available()
    if not is_available:
        messages.error(request, unavailable_msg)
        return redirect('home')

    # Feature 3: Check retake limits
    student_attempts = Result.objects.filter(student=request.user, exam=exam).count()
    if exam.max_attempts > 0 and student_attempts >= exam.max_attempts:
        messages.error(request, f"Bạn đã hết số lần làm bài cho đề thi này (tối đa {exam.max_attempts} lần).")
        return redirect('home')

    questions = list(exam.questions.all())
    
    # Feature 4: Randomize questions if enabled
    import random
    randomization_seed = None
    if exam.randomize_questions or exam.randomize_options:
        randomization_seed = random.randint(0, 999999)
        random.seed(randomization_seed)
        if exam.randomize_questions:
            random.shuffle(questions)

    context = {
        'exam': exam,
        'questions': questions,
        'randomization_seed': randomization_seed,
        'remaining_attempts': exam.max_attempts - student_attempts if exam.max_attempts > 0 else 'Vô hạn',
    }
    return render(request, 'quiz/exam.html', context)

@login_required
def submit_quiz(request, exam_id):
    if request.method != 'POST':
        return redirect('home')
        
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Feature 3: Check retake limits on submission
    student_attempts = Result.objects.filter(student=request.user, exam=exam).count()
    if exam.max_attempts > 0 and student_attempts >= exam.max_attempts:
        return HttpResponse("Bạn đã hết số lần làm bài cho đề thi này.", status=400)

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

    # Feature 3: Calculate attempt number
    attempt_number = student_attempts + 1
    
    # Feature 4: Get randomization seed from form if present
    randomization_seed = request.POST.get('randomization_seed')
    randomization_seed = int(randomization_seed) if randomization_seed else None

    result = Result.objects.create(
        student=request.user,
        exam=exam,
        correct_answers=correct_answers,
        total_questions=total_questions,
        score=score,
        answers_json=json.dumps(answers_dict),
        attempt_number=attempt_number,
        randomization_seed=randomization_seed,
    )

    messages.success(request, f"Nộp bài lần {attempt_number} thành công! Bạn đúng {correct_answers}/{total_questions} câu. Điểm số: {score}")
    return render(request, 'quiz/result.html', {'result': result})

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
    questions = list(exam.questions.all())
    
    # Feature 4: Re-apply same randomization to show questions in same order as student took them
    import random
    if result.randomization_seed is not None:
        random.seed(result.randomization_seed)
        if exam.randomize_questions:
            random.shuffle(questions)
    
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
        
        # Feature 4: Randomize options display if enabled
        options = {'A': q.option_a, 'B': q.option_b, 'C': q.option_c, 'D': q.option_d}
        correct_option = q.correct_option
        
        if exam.randomize_options and result.randomization_seed is not None:
            random.seed(result.randomization_seed + q.id)  # Consistent seed per question
            option_order = ['A', 'B', 'C', 'D']
            random.shuffle(option_order)
            options = {opt: options[opt] for opt in option_order}
            # Map back the correct option to its new position
            correct_option = [opt for opt in option_order if options[opt] == q.option_a and q.correct_option == 'A' or 
                            options[opt] == q.option_b and q.correct_option == 'B' or
                            options[opt] == q.option_c and q.correct_option == 'C' or
                            options[opt] == q.option_d and q.correct_option == 'D'][0] if q.correct_option else None
        
        questions_review.append({
            'question_text': q.question_text,
            'option_a': options.get('A', q.option_a),
            'option_b': options.get('B', q.option_b),
            'option_c': options.get('C', q.option_c),
            'option_d': options.get('D', q.option_d),
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
def analytics_dashboard(request):
    # 1. Lấy danh sách tất cả đề thi để hiển thị ở bộ lọc (Dropdown)
    exams = Exam.objects.all()
    
    # 2. Kiểm tra xem người dùng có lọc theo đề thi cụ thể nào không
    exam_id = request.GET.get('exam_id')
    selected_exam = None
    
    # Khởi tạo QuerySet cho Results và Questions ban đầu
    results = Result.objects.all()
    
    if exam_id:
        try:
            selected_exam = Exam.objects.get(id=exam_id)
            results = results.filter(exam=selected_exam)
        except Exam.DoesNotExist:
            pass

    # 3. Tính toán các chỉ số Key Metrics (Tổng lượt nộp, Điểm TB, Cao nhất, Thấp nhất)
    total_submissions = results.count()
    
    if total_submissions > 0:
        # Làm tròn điểm trung bình đến 2 chữ số thập phân
        avg_score = round(results.aggregate(Avg('score'))['score__avg'] or 0, 2)
        max_score = results.aggregate(Max('score'))['score__max']
        min_score = results.aggregate(Min('score'))['score__min']
    else:
        avg_score = 0
        max_score = 0
        min_score = 0

    stats = {
        'total_submissions': total_submissions,
        'avg_score': avg_score,
        'max_score': max_score,
        'min_score': min_score
    }

    # 4. Lấy danh sách Top 5 học sinh xuất sắc nhất (Sắp xếp theo điểm giảm dần)
    top_performers = results.order_by('-score')[:5]

    # 5. Phân tích phân bố điểm thành mảng 5 cột: ['0-2', '2-4', '4-6', '6-8', '8-10']
    # Khởi tạo mảng ban đầu toàn số 0 để đếm số lượng học sinh rơi vào từng khoảng điểm
    distribution_list = [0, 0, 0, 0, 0]
    
    for res in results:
        score = res.score
        if score < 2:
            distribution_list[0] += 1
        elif score < 4:
            distribution_list[1] += 1
        elif score < 6:
            distribution_list[2] += 1
        elif score < 8:
            distribution_list[3] += 1
        else:
            distribution_list[4] += 1  # Điểm từ 8 đến 10

    # Chuyển đổi mảng Python thành chuỗi JSON dạng sạch để truyền vào HTML
    score_data_json = json.dumps(distribution_list)

    # 6. Phân tích độ khó từng câu hỏi (Chỉ thực hiện khi giáo viên chọn một đề thi cụ thể)
    question_stats = []
    if selected_exam:
        # Lấy tất cả câu hỏi thuộc đề thi này
        questions = Question.objects.filter(exam=selected_exam)
        
        for q in questions:
            # Tìm tất cả các kết quả thi của đề thi này
            # Lưu ý: Bạn cần có logic bóc tách answers_json trong Result để đếm đúng/sai chính xác.
            # Dưới đây là logic giả định hoặc bạn có thể đếm dựa theo cách lưu kết quả của bạn:
            
            total_answers = total_submissions
            correct_count = 0
            
            # Giả định đọc từ answers_json để kiểm tra câu hỏi này học sinh chọn đúng hay sai
            for res in results:
                try:
                    answers = json.loads(res.answers_json or '{}')
                    # Nếu câu trả lời của học sinh trùng với đáp án đúng của câu hỏi
                    if answers.get(str(q.id)) == q.correct_option:
                        correct_count += 1
                except:
                    pass
            
            # Tính tỷ lệ làm đúng (Pass Rate)
            pass_rate = round((correct_count / total_answers * 100), 1) if total_answers > 0 else 0
            
            # Phân loại độ khó dựa trên tỷ lệ làm đúng
            if pass_rate >= 75:
                difficulty = "Dễ"
            elif pass_rate >= 50:
                difficulty = "Trung bình"
            else:
                difficulty = "Khó"
                
            question_stats.append({
                'question': q.question_text[:60] + '...' if len(q.question_text) > 60 else q.question_text,
                'correct': correct_count,
                'total': total_answers,
                'pass_rate': pass_rate,
                'difficulty': difficulty
            })

    # 7. Danh sách toàn bộ bài nộp gần đây (Hiển thị ở bảng cuối trang)
    # Sắp xếp theo thời gian nộp mới nhất, giới hạn lấy 10 bài gần nhất (hoặc tùy bạn chỉnh)
    recent_results = results.order_by('-completed_at')[:10]

    # Đóng gói dữ liệu truyền sang file template HTML
    context = {
        'exams': exams,
        'selected_exam': selected_exam,
        'stats': stats,
        'top_performers': top_performers,
        'score_data': score_data_json,  # Chuỗi JSON dạng mảng sạch đã qua json.dumps()
        'question_stats': question_stats,
        'results': recent_results,
    }
    
    return render(request, 'quiz/analytics.html', context)

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