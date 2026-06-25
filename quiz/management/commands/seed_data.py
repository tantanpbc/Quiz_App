import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from quiz.models import (
    Classroom, Exam, Question, Result, QuizSession, 
    ExamConstraintPreset, ExamGradeRule, ExamQuestionPool
)

class Command(BaseCommand):
    help = 'Dọn sạch database (giữ lại Admin) và nạp 10 đề thi đa dạng cùng thông tin học sinh với mật khẩu 123456'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('⚡ Bắt đầu quá trình dọn dẹp và nạp hệ thống 10 đề thi mẫu...'))

        # --- 1. XÓA DATA CŨ (GIỮ LẠI ADMIN) ---
        self.stdout.write('🧹 Đang xóa sạch dữ liệu cũ...')
        QuizSession.objects.all().delete()
        Result.objects.all().delete()
        Question.objects.all().delete()
        ExamGradeRule.objects.all().delete()
        ExamQuestionPool.objects.all().delete()
        Exam.objects.all().delete()
        Classroom.objects.all().delete()
        ExamConstraintPreset.objects.all().delete()
        
        # Xóa tất cả user ngoại trừ Superuser (Admin)
        User.objects.filter(is_superuser=False).delete()

        # --- 2. TẠO USER (GIÁO VIÊN & HỌC SINH) MẬT KHẨU: 123456 ---
        self.stdout.write('👤 Đang tạo tài khoản giáo viên và học sinh với mật khẩu: 123456...')
        
        # Tạo 3 Giáo viên
        gv_dung = User.objects.create_user(username='teacher_dung', password='123456', is_staff=True)
        gv_hoa = User.objects.create_user(username='teacher_hoa', password='123456', is_staff=True)
        gv_tam = User.objects.create_user(username='teacher_tam', password='123456', is_staff=True)
        teachers = [gv_dung, gv_hoa, gv_tam]

        # Tạo 12 Học sinh
        students = []
        for i in range(1, 13):
            student = User.objects.create_user(username=f'student_{i}', password='123456')
            students.append(student)

        # --- 3. TẠO LỚP HỌC (CLASSROOM) ---
        self.stdout.write('🏫 Đang thiết lập các lớp học...')
        class_toan = Classroom.objects.create(name='Lớp Khoa học Tự nhiên (Toán - Lý)')
        class_van = Classroom.objects.create(name='Lớp Khoa học Xã hội (Văn - Sử)')
        class_anh = Classroom.objects.create(name='Lớp Chuyên Ngoại Ngữ (Tiếng Anh)')

        # Phân phối học sinh vào các lớp
        class_toan.students.set(students[0:5])   # student_1 -> student_5
        class_van.students.set(students[5:9])    # student_6 -> student_9
        class_anh.students.set(students[8:12])   # student_9 -> student_12 (Học sinh 9 học cả Văn và Anh)

        # --- 4. TẠO DANH SÁCH 10 ĐỀ THI PHÂN HÓA PHONG PHÚ ---
        self.stdout.write('📝 Đang thiết lập cấu trúc cho 10 đề thi mẫu...')
        now = timezone.now()
        
        # Biến cấu hình mật khẩu đề thi chung
        PASS_PROTECT_KEY = "123456"

        # Danh sách định nghĩa 10 đề thi khác biệt hoàn toàn
        exams_config = [
            {
                "title": "Đề 1: Trắc nghiệm Toán đại số - 15 phút đầu giờ",
                "duration": 15, "classroom": class_toan, "teacher": gv_dung, "num_q": 5, "max_attempts": 3,
                "passing_percentage": 40, "shuffle_q": False, "shuffle_o": False, "password": "",
                "desc": "Bài kiểm tra điều kiện cấp độ nhận biết. Cho phép làm lại tối đa 3 lần để cải thiện điểm số.",
                "start": None, "end": None
            },
            {
                "title": "Đề 2: Thi Giữa Học Kỳ I - Vật Lý Đại Cương",
                "duration": 45, "classroom": class_toan, "teacher": gv_hoa, "num_q": 10, "max_attempts": 1,
                "passing_percentage": 50, "shuffle_q": True, "shuffle_o": True, "password": PASS_PROTECT_KEY,
                "desc": "Bài thi chính thức giữa kỳ. Đề có xáo trộn câu hỏi và đáp án. Cần mật khẩu để mở khóa.",
                "start": now - timedelta(days=1), "end": now + timedelta(days=3)
            },
            {
                "title": "Đề 3: Kiểm tra Đọc hiểu Ngữ Văn - Thơ cách mạng Việt Nam",
                "duration": 30, "classroom": class_van, "teacher": gv_tam, "num_q": 6, "max_attempts": 1,
                "passing_percentage": 50, "shuffle_q": False, "shuffle_o": True, "password": "",
                "desc": "Đề kiểm tra kiến thức đọc hiểu văn bản trắc nghiệm lớp Xã hội.",
                "start": now - timedelta(hours=12), "end": now + timedelta(days=1)
            },
            {
                "title": "Đề 4: Đề luyện tập Ngữ Pháp Tiếng Anh nâng cao (B2/C1)",
                "duration": 60, "classroom": class_anh, "teacher": gv_dung, "num_q": 15, "max_attempts": 5,
                "passing_percentage": 60, "shuffle_q": True, "shuffle_o": False, "password": "",
                "desc": "Bài ôn tập tự do phục vụ kỳ thi học sinh giỏi. Làm tối đa 5 lần.",
                "start": None, "end": None
            },
            {
                "title": "Đề 5: Sát hạch định kỳ Lịch Sử thế giới cận đại",
                "duration": 20, "classroom": class_van, "teacher": gv_tam, "num_q": 8, "max_attempts": 2,
                "passing_percentage": 50, "shuffle_q": True, "shuffle_o": True, "password": PASS_PROTECT_KEY,
                "desc": "Bài thi trắc nghiệm lịch sử yêu cầu ghi nhớ mốc thời gian sự kiện quan trọng. Có mật khẩu.",
                "start": now - timedelta(days=2), "end": now + timedelta(days=2)
            },
            {
                "title": "Đề 6: Khảo sát hình học không gian nâng cao (Dùng Question Pool)",
                "duration": 90, "classroom": class_toan, "teacher": gv_dung, "num_q": 20, "max_attempts": 2,
                "passing_percentage": 70, "shuffle_q": True, "shuffle_o": True, "password": "",
                "desc": "Đề thi đặc biệt: Tạo ngẫu nhiên. Kho đề có 20 câu, hệ thống tự động bốc ngẫu nhiên 12 câu cho thí sinh.",
                "start": None, "end": None, "use_pool_feature": True, "pool_select": 12
            },
            {
                "title": "Đề 7: Thi thử Tiếng Anh THPT Quốc Gia - Đợt 1",
                "duration": 60, "classroom": class_anh, "teacher": gv_dung, "num_q": 12, "max_attempts": 1,
                "passing_percentage": 50, "shuffle_q": True, "shuffle_o": True, "password": PASS_PROTECT_KEY,
                "desc": "Đề thi thử nghiêm túc theo ma trận đề của Bộ Giáo dục. Có mật mã bảo mật nghiêm ngặt.",
                "start": now - timedelta(hours=2), "end": now + timedelta(hours=6)
            },
            {
                "title": "Đề 8: Kiểm tra trắc nghiệm Vật Lý - Chương Động Lực Học",
                "duration": 40, "classroom": class_toan, "teacher": gv_hoa, "num_q": 10, "max_attempts": 2,
                "passing_percentage": 50, "shuffle_q": False, "shuffle_o": False, "password": "",
                "desc": "Bài luyện tập tính toán bài tập cơ học.",
                "start": None, "end": None
            },
            {
                "title": "Đề 9: Khảo sát kiến thức Ngữ Văn lớp 12 (Đã khóa/Hết hạn)",
                "duration": 45, "classroom": class_van, "teacher": gv_tam, "num_q": 5, "max_attempts": 1,
                "passing_percentage": 50, "shuffle_q": False, "shuffle_o": False, "password": "",
                "desc": "Hệ thống lưu trữ đề kiểm tra cũ của tuần trước. Trạng thái hiện tại: Đã đóng.",
                "start": now - timedelta(days=10), "end": now - timedelta(days=2)
            },
            {
                "title": "Đề 10: Mini-test Tiếng Anh giao tiếp công sở",
                "duration": 10, "classroom": class_anh, "teacher": gv_dung, "num_q": 4, "max_attempts": 10,
                "passing_percentage": 75, "shuffle_q": True, "shuffle_o": True, "password": "",
                "desc": "Bài test siêu ngắn giúp củng cố phản xạ từ vựng hằng ngày.",
                "start": None, "end": None
            }
        ]

        created_exams = []

        for conf in exams_config:
            exam = Exam.objects.create(
                title=conf["title"],
                duration=conf["duration"],
                classroom=conf["classroom"],
                teacher=conf["teacher"],
                description=conf["desc"],
                max_attempts=conf["max_attempts"],
                passing_percentage=conf["passing_percentage"],
                randomize_questions=conf["shuffle_q"],
                randomize_options=conf["shuffle_o"],
                password_protect=conf["password"],
                start_date=conf["start"],
                end_date=conf["end"],
                is_published=True
            )
            created_exams.append(exam)

            # Sinh câu hỏi mẫu tự động
            for q_idx in range(1, conf["num_q"] + 1):
                Question.objects.create(
                    exam=exam,
                    question_text=f"Câu hỏi trắc nghiệm thứ {q_idx}: Đây là nội dung câu hỏi giả định của [{exam.title}]?",
                    option_a=f"Phương án trả lời lựa chọn A",
                    option_b=f"Phương án trả lời lựa chọn B",
                    option_c=f"Phương án trả lời lựa chọn C",
                    option_d=f"Phương án trả lời lựa chọn D",
                    correct_option=random.choice(['A', 'B', 'C', 'D']),
                    order=q_idx
                )
            
            # Cấu hình luật điểm riêng (Grade Rule) cho các bài thi chính thức (Đề 2 và Đề 7)
            if conf["password"] == PASS_PROTECT_KEY:
                ExamGradeRule.objects.create(
                    exam=exam,
                    grade_a_min=90, grade_b_min=80, grade_c_min=70, grade_d_min=60
                )

            # Cấu hình bổ sung Pool câu hỏi ngẫu nhiên cho Đề 6
            if conf.get("use_pool_feature"):
                ExamQuestionPool.objects.create(
                    exam=exam,
                    total_questions_in_pool=conf["num_q"],
                    questions_to_select=conf["pool_select"],
                    use_pool=True
                )

        # --- 5. TẠO LỊCH SỬ LÀM BÀI TRỘN LẪN (RESULTS & SESSIONS) ---
        self.stdout.write('📊 Đang đồng bộ kết quả làm bài ảo để dựng biểu đồ báo cáo...')

        # Lớp Toán làm Đề 1 và Đề 2
        for student in class_toan.students.all():
            # Đề 1 (Làm lượt 1)
            Result.objects.create(
                student=student, exam=created_exams[0], correct_answers=random.randint(2, 5),
                total_questions=5, score=random.choice([4.0, 6.0, 8.0, 10.0]), attempt_number=1
            )
            # Một vài em làm thêm lượt 2 của Đề 1
            if random.choice([True, False]):
                Result.objects.create(
                    student=student, exam=created_exams[0], correct_answers=5,
                    total_questions=5, score=10.0, attempt_number=2
                )
            
            # Đề 2 (Đề thi giữa kỳ khó, làm đúng 1 lần)
            if student.username != 'student_5': # Cho học sinh số 5 chưa làm bài để test giao diện chưa thi
                correct_ans = random.randint(5, 10)
                Result.objects.create(
                    student=student, exam=created_exams[1], correct_answers=correct_ans,
                    total_questions=10, score=float(correct_ans), attempt_number=1,
                    randomization_seed=random.randint(1000, 9999)
                )
                QuizSession.objects.create(student=student, exam=created_exams[1], is_completed=True)

        # Lớp Văn làm Đề 3
        for student in class_van.students.all():
            Result.objects.create(
                student=student, exam=created_exams[2], correct_answers=random.randint(3, 6),
                total_questions=6, score=random.choice([5.0, 6.5, 8.0, 10.0]), attempt_number=1
            )

        # Giả lập Session đang làm dở chưa nộp bài tại Đề 4 (Tiếng Anh chuyên sâu)
        for student in class_anh.students.all()[:2]:
            QuizSession.objects.create(student=student, exam=created_exams[3], is_completed=False)

        self.stdout.write(self.style.SUCCESS('🎉 Hoàn thành! Hệ thống đã nạp xong 10 đề thi, dữ liệu tài khoản & mật mã đồng bộ về "123456".'))