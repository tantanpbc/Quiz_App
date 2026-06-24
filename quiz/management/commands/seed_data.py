from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from quiz.models import Classroom, Exam, Question, Result
import json
import random

class Command(BaseCommand):
    help = 'Làm sạch database (giữ lại Admin) và nạp đại dữ liệu kiểm thử chuẩn 4 câu hỏi'

    def handle(self, *args, **kwargs):
        self.stdout.write("--- BẮT ĐẦU DỌN DẸP VÀ LÀM SẠCH DATABASE ---")

        # 1. XÓA TOÀN BỘ KẾT QUẢ, CÂU HỎI, ĐỀ THI VÀ LỚP HỌC CŨ
        Result.objects.all().delete()
        Question.objects.all().delete()
        Exam.objects.all().delete()
        Classroom.objects.all().delete()
        
        # 2. XÓA TÀI KHOẢN HỌC SINH CŨ (CHỈ GIỮ LẠI TÀI KHOẢN ADMIN/TEACHER)
        # Những tài khoản có is_staff=True hoặc is_superuser=True sẽ ĐƯỢC GIỮ LẠI
        User.objects.filter(is_staff=False, is_superuser=False).delete()
        
        self.stdout.write("✓ Hệ thống đã được làm sạch hoàn toàn (Đã giữ lại tài khoản Admin).")
        self.stdout.write("--- BẮT ĐẦU ĐỔ DỮ LIỆU MỚI ĐỒNG BỘ ---")

        # 3. TẠO 4 LỚP HỌC KHÁC NHAU
        classes = {}
        class_names = ["Lớp AI-K26", "Lớp Python-Basic", "Lớp Web-Django", "Lớp Data-Science"]
        for name in class_names:
            cls, _ = Classroom.objects.get_or_create(name=name)
            classes[name] = cls

        # 4. TẠO DANH SÁCH 12 HỌC SINH MỚI
        students_list = [
            {'username': 'nguyenvana', 'class': 'Lớp AI-K26'},
            {'username': 'tranthib', 'class': 'Lớp AI-K26'},
            {'username': 'lequangc', 'class': 'Lớp AI-K26'},
            
            {'username': 'phamvand', 'class': 'Lớp Python-Basic'},
            {'username': 'hoangthie', 'class': 'Lớp Python-Basic'},
            {'username': 'vutuanf', 'class': 'Lớp Python-Basic'},
            
            {'username': 'buituangg', 'class': 'Lớp Web-Django'},
            {'username': 'dangthih', 'class': 'Lớp Web-Django'},
            {'username': 'nguyenvani', 'class': 'Lớp Web-Django'},
            
            {'username': 'trankienj', 'class': 'Lớp Data-Science'},
            {'username': 'maithil', 'class': 'Lớp Data-Science'},
            {'username': 'duongvanm', 'class': 'Lớp Data-Science'},
        ]

        users_pool = []
        for s in students_list:
            user = User.objects.create_user(username=s['username'], password='123456')
            classes[s['class']].students.add(user)
            users_pool.append({'user': user, 'class_name': s['class']})

        # 5. TẠO 6 ĐỀ THI
        exams_data = [
            {'title': 'Khảo sát Kiến thức Artificial Intelligence', 'duration': 15, 'class': 'Lớp AI-K26'},
            {'title': 'Kiểm tra Giữa kỳ Mạng Nơ-ron (Deep Learning)', 'duration': 20, 'class': 'Lớp AI-K26'},
            {'title': 'Trắc nghiệm Python Core Cơ Bản', 'duration': 10, 'class': 'Lớp Python-Basic'},
            {'title': 'Lập trình Hướng đối tượng với Python OOP', 'duration': 15, 'class': 'Lớp Python-Basic'},
            {'title': 'Xây dựng Web Backend với Django Framework', 'duration': 30, 'class': 'Lớp Web-Django'},
            {'title': 'Toán Xác suất & Phân tích Dữ liệu lớn', 'duration': 25, 'class': 'Lớp Data-Science'},
        ]

        created_exams = []
        for e_data in exams_data:
            exam = Exam.objects.create(
                title=e_data['title'],
                duration=e_data['duration'],
                classroom=classes[e_data['class']]
            )
            created_exams.append(exam)

        # 6. NẠP NỘI DUNG CÂU HỎI (MỖI ĐỀ ĐỀU CÓ CHUẨN ĐÚNG 4 CÂU HỎI)
        qa_bank = [
            ("Câu hỏi số 1: Đâu là phương pháp học máy?", "A. Học có giám sát", "B. Học không giám sát", "C. Học tăng cường", "D. Tất cả đều đúng", "D"),
            ("Câu hỏi số 2: Đâu không phải thư viện AI?", "A. TensorFlow", "B. PyTorch", "C. Django", "D. Scikit-Learn", "C"),
            ("Câu hỏi số 3: Lệnh nào dùng để xuất dữ liệu ra màn hình?", "A. input()", "B. print()", "C. log()", "D. output()", "B"),
            ("Câu hỏi số 4: Đâu là kiểu dữ liệu danh sách thay đổi được?", "A. Tuple", "B. String", "C. List", "D. Integer", "C"),
        ]

        for exam in created_exams:
            for idx, qa in enumerate(qa_bank):
                Question.objects.create(
                    exam=exam,
                    question_text=f"[{exam.title}] - {qa[0]}",
                    option_a=qa[1], option_b=qa[2], option_c=qa[3], option_d=qa[4],
                    correct_option=qa[5]
                )

        # 7. TỰ ĐỘNG SINH CÁC LƯỢT THI GIẢ LẬP ĐỒNG BỘ ĐỀU 4 CÂU HỎI
        options_choices = ['A', 'B', 'C', 'D']
        result_count = 0

        for student_info in users_pool:
            student = student_info['user']
            student_class = student_info['class_name']

            for exam in created_exams:
                # Chỉ sinh dữ liệu cho học sinh làm đề thi thuộc đúng lớp của mình
                if exam.classroom.name == student_class:
                    correct = random.randint(1, 4)  # Số câu đúng ngẫu nhiên từ 1 đến 4
                    score = round((correct / 4) * 10, 2)  # Quy đổi ra thang điểm 10 chuẩn
                    
                    ans_dict = {
                        "1": random.choice(options_choices),
                        "2": random.choice(options_choices),
                        "3": random.choice(options_choices),
                        "4": random.choice(options_choices)
                    }

                    Result.objects.create(
                        student=student,
                        exam=exam,
                        correct_answers=correct,
                        total_questions=4,  # Ép buộc đồng bộ tất cả lượt làm bài đều tính trên tổng số 4 câu hỏi
                        score=score,
                        answers_json=json.dumps(ans_dict)
                    )
                    result_count += 1

        self.stdout.write(f"✓ Đã tạo thành công {result_count} lượt nộp bài chuẩn 4 câu hỏi.")
        self.stdout.write(self.style.SUCCESS("=== TOÀN BỘ DỮ LIỆU ĐÃ ĐƯỢC LÀM SẠCH VÀ TÁI CẤU TRÚC ĐỒNG BỘ ==="))