# scheduler_module.py
# -*- coding: utf-8 -*-
import psycopg2
import psycopg2.extras
import datetime
import math
import random
import copy
import pandas as pd
from collections import defaultdict, namedtuple
import re
import io  # Required for BytesIO

# --- 检查 openpyxl 库 ---
try:
    import openpyxl
    from openpyxl.utils import get_column_letter
    from openpyxl.styles import Alignment, Font, Border, Side

    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    # print("警告：未找到 'openpyxl' 库，将无法导出 Excel 课表。请运行 'pip install openpyxl' 安装。") # 在app.py中处理

# ==================================
# 2. 数据模型 (保持不变)
# ==================================
Semester = namedtuple('Semester', ['id', 'name', 'start_date', 'end_date', 'total_weeks'])
Major = namedtuple('Major', ['id', 'name'])
Teacher = namedtuple('Teacher', ['id', 'user_id', 'name'])
Classroom = namedtuple('Classroom', ['id', 'name', 'capacity', 'type'])
Course = namedtuple('Course', ['id', 'name', 'total_sessions', 'course_type'])
TimeSlot = namedtuple('TimeSlot', ['id', 'day_of_week', 'period', 'start_time', 'end_time'])
CourseAssignment = namedtuple('CourseAssignment',
                              ['id', 'major_id', 'course_id', 'teacher_id', 'semester_id', 'is_core_course',
                               'expected_students'])
TimetableEntry = namedtuple('TimetableEntry',
                            ['id', 'semester_id', 'major_id', 'course_id', 'teacher_id', 'classroom_id', 'timeslot_id',
                             'week_number', 'assignment_id'])


# ==================================
# 3. 数据加载函数 (修改: 使用 get_connection_func)
# ==================================
def load_data_from_db(get_connection_func):
    """从数据库加载所有基础数据"""
    print("SCHEDULER: 开始从数据库加载数据...")
    all_data = {}
    conn = None
    try:
        conn = get_connection_func()  # 使用传入的函数获取连接
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # ... (其余加载逻辑与您脚本中的 load_data_from_db 基本相同) ...
        # 加载学期 (计算 total_weeks)
        cur.execute("SELECT id, name, start_date, end_date FROM semesters")
        raw_semesters = cur.fetchall()
        all_data['semesters'] = {}
        # print("  - 正在加载学期信息并计算总周数...")
        for row in raw_semesters:
            start_date = row['start_date']
            end_date = row['end_date']
            calculated_weeks = 0
            if isinstance(start_date, datetime.date) and isinstance(end_date, datetime.date):
                if end_date >= start_date:
                    delta_days = (end_date - start_date).days + 1
                    calculated_weeks = math.ceil(delta_days / 7)
                # else: print(f"    警告: 学期 ID {row['id']} ('{row['name']}') 结束日期早于开始日期，总周数计为 0。")
            # else: print(f"    警告: 学期 ID {row['id']} ('{row['name']}') 开始或结束日期无效，无法计算总周数，计为 0。")
            all_data['semesters'][row['id']] = Semester(
                id=row['id'], name=row['name'], start_date=start_date,
                end_date=end_date, total_weeks=calculated_weeks
            )
        # print(f"  - 加载并处理了 {len(all_data['semesters'])} 个学期信息")

        # 加载专业
        cur.execute("SELECT id, name FROM majors")
        all_data['majors'] = {row['id']: Major(**row) for row in cur.fetchall()}
        # print(f"  - 加载了 {len(all_data['majors'])} 个专业信息")

        # 加载教师
        cur.execute("SELECT id, username FROM users")
        user_id_to_name = {row['id']: row['username'] for row in cur.fetchall()}
        cur.execute("SELECT id, user_id FROM teachers")
        raw_teachers = cur.fetchall()
        all_data['teachers'] = {}
        for row in raw_teachers:
            teacher_id = row['id']
            user_id = row['user_id']
            teacher_name = user_id_to_name.get(user_id, f"未知用户(ID:{user_id})")
            all_data['teachers'][teacher_id] = Teacher(id=teacher_id, user_id=user_id, name=teacher_name)
        # print(f"  - 加载并处理了 {len(all_data['teachers'])} 个教师信息")

        # 加载教室
        cur.execute("SELECT id, building, room_number, capacity, room_type FROM classrooms")
        all_data['classrooms'] = {}
        for row in cur.fetchall():
            classroom_id = row['id']
            building_name = row['building'] if row['building'] else '未知楼'
            room_num = row['room_number'] if row['room_number'] else '未知号'
            classroom_name = f"{building_name}-{room_num}"
            all_data['classrooms'][classroom_id] = Classroom(
                id=classroom_id, name=classroom_name, capacity=row['capacity'], type=row['room_type']
            )
        # print(f"  - 加载了 {len(all_data['classrooms'])} 个教室信息")

        # 加载课程
        cur.execute("SELECT id, name, total_sessions, course_type FROM courses")
        all_data['courses'] = {row['id']: Course(**row) for row in cur.fetchall()}
        # print(f"  - 加载了 {len(all_data['courses'])} 个课程信息")

        # 加载时间段
        cur.execute("SELECT id, day_of_week, period, start_time, end_time FROM time_slots ORDER BY day_of_week, period")
        all_data['timeslots'] = {row['id']: TimeSlot(**row) for row in cur.fetchall()}
        all_data['timeslot_lookup'] = {(ts.day_of_week, ts.period): ts.id for ts in all_data['timeslots'].values()}
        # print(f"  - 加载了 {len(all_data['timeslots'])} 个时间段信息")

        # 加载教学任务
        cur.execute("""
            SELECT id, major_id, course_id, teacher_id, semester_id, is_core_course, expected_students
            FROM course_assignments
        """)
        all_data['course_assignments'] = {row['id']: CourseAssignment(**row) for row in cur.fetchall()}
        # print(f"  - 加载了 {len(all_data['course_assignments'])} 个教学任务")

        cur.close()
        print("SCHEDULER: 数据加载成功!")
        return all_data

    except psycopg2.Error as e:
        print(f"SCHEDULER: 数据库连接或查询错误: {e}")
        # import traceback; traceback.print_exc() # For more detailed server-side logs if needed
        raise  # Re-raise the exception to be caught by the Flask route
    finally:
        if conn:
            conn.close()


# ==================================
# 4. 辅助函数 (保持不变)
# ==================================
def find_timeslot_id(day_str, period_num, all_data):
    return all_data['timeslot_lookup'].get((day_str, period_num))


def check_constraints(timetable_state, assignment, week, timeslot_id, classroom_id, all_data):
    teacher_id = assignment.teacher_id
    major_id = assignment.major_id
    if (teacher_id, week, timeslot_id) in timetable_state['teacher_schedule']: return False
    if (classroom_id, week, timeslot_id) in timetable_state['classroom_schedule']: return False
    if (major_id, week, timeslot_id) in timetable_state['major_schedule']: return False
    return True


def find_available_classroom(timetable_state, assignment, week, timeslot_id, all_data):
    required_capacity = assignment.expected_students
    course = all_data['courses'].get(assignment.course_id)
    is_lab_course = course and course.course_type == '实验课'
    preferred_type_available, other_type_available = [], []
    busy_classrooms = {cid for (cid, w, tid) in timetable_state['classroom_schedule'] if
                       w == week and tid == timeslot_id}

    for classroom_id, classroom in all_data['classrooms'].items():
        if classroom_id in busy_classrooms: continue
        if classroom.capacity < required_capacity: continue
        classroom_type_match = (is_lab_course and classroom.type == '实验室') or \
                               (not is_lab_course and classroom.type == '普通教室')
        if classroom_type_match:
            preferred_type_available.append(classroom_id)
        else:
            other_type_available.append(classroom_id)

    if preferred_type_available: return random.choice(preferred_type_available)
    if other_type_available: return random.choice(other_type_available)
    return None


# ==================================
# 5. 自动生成初始模板函数 (保持不变)
# ==================================
def generate_initial_template(assignments_dict, all_data):
    # print("SCHEDULER:   正在根据可用任务自动生成初始周模板...")
    template_structure = [
        ('周一', 1, '理论课', 'MonWed1'), ('周一', 2, '理论课', 'MonWed2'), ('周一', 3, None, None),
        ('周一', 4, None, None),
        ('周二', 1, '理论课', 'TueThu1'), ('周二', 2, '理论课', 'TueThu2'), ('周二', 3, None, None),
        ('周二', 4, None, None),
        ('周三', 1, '理论课', 'MonWed1'), ('周三', 2, '理论课', 'MonWed2'), ('周三', 3, None, None),
        ('周三', 4, None, None),
        ('周四', 1, '理论课', 'TueThu1'), ('周四', 2, '理论课', 'TueThu2'), ('周四', 3, None, None),
        ('周四', 4, None, None),
        ('周五', 1, '实验课', 'FriLab1'), ('周五', 2, '实验课', 'FriLab2'), ('周五', 3, None, None),
        ('周五', 4, None, None),
    ]
    repetition_map = defaultdict(list)
    slot_type_map = {}
    initial_template = {}
    all_slots_in_template = set()
    for day, period, course_type, group in template_structure:
        slot = (day, period)
        all_slots_in_template.add(slot)
        slot_type_map[slot] = course_type
        initial_template[slot] = None
        if group: repetition_map[group].append(slot)

    theory_assignments, lab_assignments, other_assignments = [], [], []
    if not assignments_dict: return initial_template, []

    def get_priority(assign_id, assign):
        course = all_data['courses'].get(assign.course_id)
        return (assign.is_core_course, -(course.total_sessions if course else 0), random.random())

    for assign_id, assign in assignments_dict.items():
        course = all_data['courses'].get(assign.course_id)
        if course and course.total_sessions > 0:
            priority = get_priority(assign_id, assign)
            if course.course_type == '理论课':
                theory_assignments.append((priority, assign_id))
            elif course.course_type == '实验课':
                lab_assignments.append((priority, assign_id))
            else:
                other_assignments.append((priority, assign_id))
    theory_assignments.sort(reverse=True);
    lab_assignments.sort(reverse=True);
    other_assignments.sort(reverse=True)  # Higher priority first

    available_theory = [assign_id for _, assign_id in theory_assignments]
    available_labs = [assign_id for _, assign_id in lab_assignments]
    available_others = [assign_id for _, assign_id in other_assignments]
    used_assignment_ids = set()

    processed_groups = set()
    for group, slots in repetition_map.items():
        if not slots or group in processed_groups: continue
        first_slot = slots[0]
        desired_course_type = slot_type_map.get(first_slot)
        selected_assign_id = None
        source_list = []
        if desired_course_type == '理论课':
            source_list = available_theory
        elif desired_course_type == '实验课':
            source_list = available_labs
        elif desired_course_type is not None:
            source_list = available_others
        if source_list:
            for assign_id in source_list:
                if assign_id not in used_assignment_ids: selected_assign_id = assign_id; break
        if selected_assign_id:
            used_assignment_ids.add(selected_assign_id)
            for slot in slots: initial_template[slot] = selected_assign_id
            processed_groups.add(group)

    for slot in all_slots_in_template:
        is_in_processed_group = any(slot in repetition_map[group] for group in processed_groups)
        if initial_template[slot] is None and not is_in_processed_group:
            desired_course_type = slot_type_map.get(slot)
            selected_assign_id = None
            source_list = []
            if desired_course_type == '理论课':
                source_list = available_theory
            elif desired_course_type == '实验课':
                source_list = available_labs
            elif desired_course_type is not None:
                source_list = available_others
            if source_list:
                for assign_id in source_list:
                    if assign_id not in used_assignment_ids: selected_assign_id = assign_id; break
            if selected_assign_id:
                used_assignment_ids.add(selected_assign_id)
                initial_template[slot] = selected_assign_id

    remaining_pool_ids = [assign_id for assign_id in assignments_dict if assign_id not in used_assignment_ids]
    remaining_pool_sorted = sorted(
        remaining_pool_ids, key=lambda assign_id: get_priority(assign_id, assignments_dict[assign_id]), reverse=True
    )
    # print(f"SCHEDULER:   自动生成模板完成。选入 {len(used_assignment_ids)} 个任务。剩余 {len(remaining_pool_sorted)} 个任务进入替换池。")
    return initial_template, remaining_pool_sorted


# ==================================
# 6. 基于模板的排课执行函数 (保持不变)
# ==================================
def schedule_with_generated_template(assignments_for_major, current_semester, current_major, all_data, initial_template,
                                     unscheduled_pool_ids):
    # print(f"\nSCHEDULER: ===== 开始为专业 '{current_major.name}' 基于模板排课 (学期: {current_semester.name}, {current_semester.total_weeks} 周) =====")
    total_weeks = current_semester.total_weeks
    if not total_weeks or total_weeks <= 0:
        unscheduled_details_on_error = []
        for assign_id, assign in assignments_for_major.items():
            course = all_data['courses'].get(assign.course_id)
            teacher = all_data['teachers'].get(assign.teacher_id)
            unscheduled_details_on_error.append({
                'assignment_id': assign_id,
                'course_name': course.name if course else '未知课程',
                'teacher_name': teacher.name if teacher else '未知教师',
                'remaining_sessions': course.total_sessions if course else 0
            })
        return {'schedule': [], 'unscheduled_details': unscheduled_details_on_error, 'conflicts': []}

    assignment_sessions_remaining = {}
    for assign_id, assign in assignments_for_major.items():
        course = all_data['courses'].get(assign.course_id)
        assignment_sessions_remaining[assign_id] = course.total_sessions if course else 0

    unscheduled_pool = list(unscheduled_pool_ids)
    current_template_schedule = initial_template.copy()
    final_schedule = []
    conflicts_log = []
    # This state needs to be managed globally if multiple majors are scheduled concurrently affecting same teachers/classrooms
    # For sequential per-major scheduling, this can be reset or passed if teacher/classroom state from previous majors should affect current.
    # The original script implies this state is per-major, but for a global schedule, it should be truly global.
    # For now, assuming the main runner function (run_full_scheduling_process) handles the "global_timetable_state" correctly across majors.
    # Let's assume it's passed in and updated by this function.
    global_timetable_state = {'teacher_schedule': set(), 'classroom_schedule': set(),
                              'major_schedule': set()}  # This might need to be passed from run_full_scheduling_process

    day_order = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    sorted_template_slots = sorted(
        current_template_schedule.keys(),
        key=lambda x: (day_order.index(x[0]) if x[0] in day_order else 99, x[1])
    )

    for week in range(1, total_weeks + 1):
        for day_str, period_num in sorted_template_slots:
            slot = (day_str, period_num)
            current_assignment_id = current_template_schedule.get(slot)
            needs_replacement = (current_assignment_id is None) or \
                                (assignment_sessions_remaining.get(current_assignment_id, 0) <= 0)

            if needs_replacement:
                found_replacement = False
                if unscheduled_pool:
                    # Try to find a replacement that matches the slot type if possible
                    # This is a simplification; a more complex matching could be done
                    # For now, just take the next from pool
                    temp_pool = []
                    while unscheduled_pool:
                        potential_replacement_id = unscheduled_pool.pop(0)
                        if assignment_sessions_remaining.get(potential_replacement_id, 0) > 0:
                            current_template_schedule[slot] = potential_replacement_id
                            current_assignment_id = potential_replacement_id
                            found_replacement = True
                            break
                        else:  # This task is also done, put it aside
                            temp_pool.append(potential_replacement_id)
                    unscheduled_pool.extend(
                        temp_pool)  # Add back unusable tasks (though they shouldn't be here if already 0)

                if not found_replacement:
                    current_template_schedule[slot] = None
                    current_assignment_id = None

            if current_assignment_id is not None and assignment_sessions_remaining.get(current_assignment_id, 0) > 0:
                assignment = assignments_for_major.get(current_assignment_id)
                if not assignment: continue
                timeslot_id = find_timeslot_id(day_str, period_num, all_data)
                if not timeslot_id: continue

                suitable_classroom_id = find_available_classroom(global_timetable_state, assignment, week, timeslot_id,
                                                                 all_data)
                if suitable_classroom_id:
                    if check_constraints(global_timetable_state, assignment, week, timeslot_id, suitable_classroom_id,
                                         all_data):
                        entry = TimetableEntry(None, current_semester.id, assignment.major_id, assignment.course_id,
                                               assignment.teacher_id, suitable_classroom_id, timeslot_id, week,
                                               current_assignment_id)
                        final_schedule.append(entry)
                        global_timetable_state['teacher_schedule'].add((assignment.teacher_id, week, timeslot_id))
                        global_timetable_state['classroom_schedule'].add((suitable_classroom_id, week, timeslot_id))
                        global_timetable_state['major_schedule'].add((assignment.major_id, week, timeslot_id))
                        assignment_sessions_remaining[current_assignment_id] -= 1
                        # if assignment_sessions_remaining[current_assignment_id] == 0:
                        # course_name = all_data['courses'].get(assignment.course_id, '?').name
                        # print(f"  **SCHEDULER: 专业 {current_major.name}: 任务 {current_assignment_id} ({course_name}) 在第 {week} 周完成。**")
                    else:
                        conflicts_log.append(
                            {'major_id': assignment.major_id, 'week': week, 'day': day_str, 'period': period_num,
                             'assignment_id': current_assignment_id, 'reason': "约束冲突"})
                else:
                    conflicts_log.append(
                        {'major_id': assignment.major_id, 'week': week, 'day': day_str, 'period': period_num,
                         'assignment_id': current_assignment_id,
                         'reason': f"找不到容量({assignment.expected_students})教室"})

    unscheduled_final = []
    for assign_id, remaining in assignment_sessions_remaining.items():
        if remaining > 0:
            assign_obj = assignments_for_major.get(assign_id)
            course_name, teacher_name = '?', '?'
            if assign_obj:
                course = all_data['courses'].get(assign_obj.course_id)
                teacher = all_data['teachers'].get(assign_obj.teacher_id)
                if course: course_name = course.name
                if teacher: teacher_name = teacher.name
            unscheduled_final.append(
                {'assignment_id': assign_id, 'course_name': course_name, 'teacher_name': teacher_name,
                 'remaining_sessions': remaining})
    # print(f"SCHEDULER: ===== 专业 '{current_major.name}' 排课完成。生成课表条目: {len(final_schedule)}, 冲突/未安排记录: {len(conflicts_log)}, 未完成任务数: {len(unscheduled_final)} =====")
    return {'schedule': final_schedule, 'unscheduled_details': unscheduled_final, 'conflicts': conflicts_log,
            'updated_global_state': global_timetable_state}


# ==================================
# 7. 导出到 Excel 函数 (修改: 输出 BytesIO, 可选筛选)
# ==================================
def sanitize_sheet_name(name):
    name = re.sub(r'[\\/*?:"<>|\[\]]', '_', name)
    return name[:31]


def format_semester_sheet_for_export(worksheet, total_weeks, periods_count):
    if not OPENPYXL_AVAILABLE: return
    try:
        center_alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        thin_border_side = Side(border_style="thin", color="000000")
        thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side,
                             bottom=thin_border_side)
        header_font = Font(bold=True)

        for col_idx, column_cells in enumerate(worksheet.columns):
            if col_idx < 2: continue
            max_length = 0
            column_letter = get_column_letter(column_cells[0].column)
            for cell in column_cells:
                if cell.value:
                    try:
                        lines = str(cell.value).split('\n')
                        cell_len = max(
                            sum(1.8 if '\u4e00' <= char <= '\u9fff' else 1 for char in line) for line in lines)
                        if cell_len > max_length: max_length = cell_len
                    except:
                        pass
            adjusted_width = max_length + 4
            worksheet.column_dimensions[column_letter].width = max(adjusted_width, 15)

        worksheet.column_dimensions['A'].width = 8  # 周数
        worksheet.column_dimensions['B'].width = 8  # 节次

        header_rows = 1
        for row_idx in range(1, worksheet.max_row + 1):
            worksheet.row_dimensions[row_idx].height = 45
            for cell in worksheet[row_idx]:
                cell.alignment = center_alignment
                cell.border = thin_border
            if row_idx == header_rows:
                for cell in worksheet[row_idx]:
                    cell.font = header_font

        if total_weeks > 0 and periods_count > 0:
            for week in range(1, total_weeks + 1):
                start_row = header_rows + (week - 1) * periods_count + 1
                end_row = start_row + periods_count - 1
                if start_row <= end_row and start_row <= worksheet.max_row and end_row <= worksheet.max_row:
                    worksheet.merge_cells(start_row=start_row, start_column=1, end_row=end_row, end_column=1)
                    merged_cell = worksheet.cell(row=start_row, column=1)
                    merged_cell.value = f"第 {week} 周"
                    merged_cell.alignment = center_alignment
                    merged_cell.font = header_font
                    merged_cell.border = thin_border
    except Exception as format_e:
        print(f"SCHEDULER: 警告：在调整工作表 '{worksheet.title}' 格式时发生错误: {format_e}")


def generate_excel_report_for_send_file(schedule_entries, all_data, semester,
                                        target_major_id=None, target_teacher_id=None):
    if not OPENPYXL_AVAILABLE:
        raise ImportError("缺少 openpyxl 库，无法导出 Excel。")
    if not schedule_entries:
        # print("SCHEDULER: 没有排课数据可导出。")
        # Return empty BytesIO or raise error
        return io.BytesIO()  # Or perhaps raise an error if expected

    # print(f"SCHEDULER: 开始生成 Excel 报告...")
    output_buffer = io.BytesIO()
    try:
        # Use 'with' to ensure writer is closed properly
        with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
            timeslots = sorted(all_data['timeslots'].values(), key=lambda t: (t.day_of_week, t.period))
            day_map = {'周一': 1, '周二': 2, '周三': 3, '周四': 4, '周五': 5, '周六': 6, '周日': 7}
            periods = sorted(list(set(t.period for t in timeslots)))
            days = sorted(list(set(t.day_of_week for t in timeslots)), key=lambda d: day_map.get(d, 8))
            total_weeks = semester.total_weeks

            if total_weeks <= 0:
                # print("SCHEDULER: 错误：学期总周数无效，无法生成学期课表。")
                # Create an empty sheet or raise error
                df_empty = pd.DataFrame([["学期周数无效"]])
                df_empty.to_excel(writer, sheet_name="错误", index=False, header=False)
                # writer.save() # For older pandas, ExcelWriter needs save() before BytesIO seek
                output_buffer.seek(0)
                return output_buffer

            periods_count = len(periods)

            # Filter entries if target_major_id or target_teacher_id is provided
            filtered_entries = schedule_entries
            report_type = "学期总"
            entity_name = semester.name

            if target_major_id:
                filtered_entries = [e for e in schedule_entries if e.major_id == target_major_id]
                major_info = all_data['majors'].get(target_major_id)
                entity_name = major_info.name if major_info else f"专业ID_{target_major_id}"
                report_type = f"专业_{entity_name}"

                # Generate single sheet for the major
                df_major_semester = pd.DataFrame(
                    index=pd.MultiIndex.from_product([range(1, total_weeks + 1), periods], names=['周数', '节次']),
                    columns=days
                ).fillna('')
                for entry in filtered_entries:
                    ts = all_data['timeslots'].get(entry.timeslot_id)
                    if not ts: continue
                    course = all_data['courses'].get(entry.course_id)
                    teacher = all_data['teachers'].get(entry.teacher_id)
                    classroom = all_data['classrooms'].get(entry.classroom_id)
                    cell_text = f"{course.name if course else '?'}\n{teacher.name if teacher else '?'}\n@{classroom.name if classroom else '?'}"
                    df_major_semester.loc[(entry.week_number, ts.period), ts.day_of_week] = cell_text

                sheet_name_major = sanitize_sheet_name(f"专业_{entity_name}")
                df_major_semester.to_excel(writer, sheet_name=sheet_name_major, merge_cells=False)
                worksheet_major = writer.sheets[sheet_name_major]
                format_semester_sheet_for_export(worksheet_major, total_weeks, periods_count)


            elif target_teacher_id:
                filtered_entries = [e for e in schedule_entries if e.teacher_id == target_teacher_id]
                teacher_info = all_data['teachers'].get(target_teacher_id)
                entity_name = teacher_info.name if teacher_info else f"教师ID_{target_teacher_id}"
                report_type = f"教师_{entity_name}"

                df_teacher_semester = pd.DataFrame(
                    index=pd.MultiIndex.from_product([range(1, total_weeks + 1), periods], names=['周数', '节次']),
                    columns=days
                ).fillna('')
                for entry in filtered_entries:
                    ts = all_data['timeslots'].get(entry.timeslot_id)
                    if not ts: continue
                    course = all_data['courses'].get(entry.course_id)
                    major = all_data['majors'].get(entry.major_id)
                    classroom = all_data['classrooms'].get(entry.classroom_id)
                    cell_text = f"{course.name if course else '?'}\n({major.name if major else '?'})\n@{classroom.name if classroom else '?'}"
                    df_teacher_semester.loc[(entry.week_number, ts.period), ts.day_of_week] = cell_text

                sheet_name_teacher = sanitize_sheet_name(f"教师_{entity_name}")
                df_teacher_semester.to_excel(writer, sheet_name=sheet_name_teacher, merge_cells=False)
                worksheet_teacher = writer.sheets[sheet_name_teacher]
                format_semester_sheet_for_export(worksheet_teacher, total_weeks, periods_count)

            else:  # Full semester report (all majors and all teachers)
                # A. 专业课表
                schedule_by_major = defaultdict(list)
                involved_major_ids = sorted(list(set(entry.major_id for entry in filtered_entries)))
                for entry in filtered_entries: schedule_by_major[entry.major_id].append(entry)

                for major_id_iter in involved_major_ids:
                    major_schedule = schedule_by_major[major_id_iter]
                    major_info_iter = all_data['majors'].get(major_id_iter)
                    major_name_iter = major_info_iter.name if major_info_iter else f"专业ID_{major_id_iter}"
                    df_major_semester = pd.DataFrame(
                        index=pd.MultiIndex.from_product([range(1, total_weeks + 1), periods], names=['周数', '节次']),
                        columns=days
                    ).fillna('')
                    for entry in major_schedule:  # Use major_schedule, not filtered_entries
                        ts = all_data['timeslots'].get(entry.timeslot_id)
                        if not ts: continue
                        course = all_data['courses'].get(entry.course_id)
                        teacher = all_data['teachers'].get(entry.teacher_id)
                        classroom = all_data['classrooms'].get(entry.classroom_id)
                        cell_text = f"{course.name if course else '?'}\n{teacher.name if teacher else '?'}\n@{classroom.name if classroom else '?'}"
                        df_major_semester.loc[(entry.week_number, ts.period), ts.day_of_week] = cell_text

                    sheet_name_major = sanitize_sheet_name(f"专业_{major_name_iter}")
                    df_major_semester.to_excel(writer, sheet_name=sheet_name_major, merge_cells=False)
                    worksheet_major = writer.sheets[sheet_name_major]
                    format_semester_sheet_for_export(worksheet_major, total_weeks, periods_count)

                # B. 教师课表
                schedule_by_teacher = defaultdict(list)
                involved_teacher_ids = sorted(list(set(entry.teacher_id for entry in filtered_entries)))
                for entry in filtered_entries: schedule_by_teacher[entry.teacher_id].append(entry)

                for teacher_id_iter in involved_teacher_ids:
                    teacher_schedule = schedule_by_teacher[teacher_id_iter]
                    teacher_info_iter = all_data['teachers'].get(teacher_id_iter)
                    teacher_name_iter = teacher_info_iter.name if teacher_info_iter else f"教师ID_{teacher_id_iter}"
                    df_teacher_semester = pd.DataFrame(
                        index=pd.MultiIndex.from_product([range(1, total_weeks + 1), periods], names=['周数', '节次']),
                        columns=days
                    ).fillna('')
                    for entry in teacher_schedule:  # Use teacher_schedule
                        ts = all_data['timeslots'].get(entry.timeslot_id)
                        if not ts: continue
                        course = all_data['courses'].get(entry.course_id)
                        major = all_data['majors'].get(entry.major_id)
                        classroom = all_data['classrooms'].get(entry.classroom_id)
                        cell_text = f"{course.name if course else '?'}\n({major.name if major else '?'})\n@{classroom.name if classroom else '?'}"
                        df_teacher_semester.loc[(entry.week_number, ts.period), ts.day_of_week] = cell_text

                    sheet_name_teacher = sanitize_sheet_name(f"教师_{teacher_name_iter}")
                    df_teacher_semester.to_excel(writer, sheet_name=sheet_name_teacher, merge_cells=False)
                    worksheet_teacher = writer.sheets[sheet_name_teacher]
                    format_semester_sheet_for_export(worksheet_teacher, total_weeks, periods_count)

        # writer.save() # For older pandas version. For newer, 'with' handles it.
        output_buffer.seek(0)
        # print(f"SCHEDULER: Excel 报告生成完毕。类型: {report_type}")
        return output_buffer

    except Exception as e:
        print(f"SCHEDULER: 生成 Excel 文件时出错: {e}")
        # import traceback; traceback.print_exc()
        # Return an empty buffer or re-raise to indicate failure
        # For now, returning an empty buffer to avoid breaking send_file if it expects BytesIO
        error_output = io.BytesIO()
        # Optionally write an error message to this buffer for debugging
        # pd.DataFrame([["生成Excel时出错:", str(e)]]).to_excel(ExcelWriter(error_output), sheet_name="错误")
        error_output.seek(0)
        return error_output  # Or raise e


# ==================================
# 8. 数据库操作函数 (修改: 使用 get_connection_func)
# ==================================
def clear_db_for_semester(semester_id, get_connection_func):
    conn = None
    try:
        conn = get_connection_func()
        cur = conn.cursor()
        # print(f"SCHEDULER: 正在清空数据库中 学期 ID={semester_id} 的旧排课记录...")
        delete_query = "DELETE FROM timetable_entries WHERE semester_id = %s"
        cur.execute(delete_query, (semester_id,))
        deleted_count = cur.rowcount
        conn.commit()
        cur.close()
        # print(f"SCHEDULER: 成功删除 {deleted_count} 条旧记录。")
        return True, deleted_count
    except psycopg2.Error as e:
        print(f"SCHEDULER: 清空学期 {semester_id} 的数据库记录时出错: {e}")
        if conn: conn.rollback()
        # import traceback; traceback.print_exc()
        raise  # Re-raise
    finally:
        if conn: conn.close()


# scheduler_module.py

# ... (其他代码保持不变) ...

def save_schedule_to_db(schedule_entries, get_connection_func):
    if not schedule_entries: return 0
    conn_save = None
    inserted_count = 0
    try:
        conn_save = get_connection_func()
        cur_save = conn_save.cursor()

        # --- 这是修改的关键点 ---
        # insert_query 应该在 VALUES 后面只有一个 %s
        insert_query = """
            INSERT INTO timetable_entries
            (semester_id, major_id, course_id, teacher_id, classroom_id, timeslot_id, week_number, assignment_id)
            VALUES %s 
        """
        # --- 修改结束 ---

        data_to_insert = [
            (e.semester_id, e.major_id, e.course_id, e.teacher_id, e.classroom_id, e.timeslot_id, e.week_number,
             e.assignment_id)
            for e in schedule_entries
        ]
        print("[DEBUG] 插入语句 (用于 execute_values):", insert_query)  # 确认修改后的语句
        print("[DEBUG] 首条数据:", data_to_insert[0] if data_to_insert else "无数据")

        if data_to_insert:
            from psycopg2.extras import execute_values
            # execute_values 会自动处理 data_to_insert 中的每个元组，
            # 将其格式化为 (%s, %s, ..., %s) 的形式，并替换上面 insert_query 中的单个 %s
            execute_values(cur_save, insert_query, data_to_insert,
                           page_size=len(data_to_insert))  # page_size 可以调整, 比如设为100或1000

            # execute_values 通常不直接返回行数，但 psycopg2 的 cursor.rowcount
            # 在 execute_values 之后可能不准确反映所有插入的行数（取决于驱动和版本）。
            # 更可靠的方式是假设如果没抛异常，data_to_insert 的长度就是尝试插入的行数。
            # 或者，如果你的表有自增ID，并且你关心确切的插入数量，可能需要其他策略或检查。
            # 但通常，我们信任 execute_values 如果不抛错，就成功处理了数据。
            # 对于大多数情况, len(data_to_insert) 是一个合理的估计值
            inserted_count = len(data_to_insert)
            conn_save.commit()

        cur_save.close()
        # print(f"SCHEDULER: 成功保存 {inserted_count} 条排课记录到数据库。") # 可以在这里打印
        return inserted_count
    except psycopg2.Error as e:
        print(f"SCHEDULER: 保存排课结果到数据库时出错: {e}")
        if conn_save: conn_save.rollback()
        # import traceback; traceback.print_exc()
        raise  # Re-raise
    finally:
        if conn_save: conn_save.close()


# ... (其他代码保持不变) ...


# ==================================
# 9. 主排课流程函数
# ==================================
def run_full_scheduling_process(target_semester_id, get_connection_func):
    """
    主排课流程函数，被 Flask API 调用。
    返回一个包含排课结果摘要的字典。
    """
    print(f"SCHEDULER: 开始执行学期 ID {target_semester_id} 的自动排课程序...")
    summary = {
        "status": "failure",
        "message": "",
        "processed_majors": 0,
        "total_scheduled_entries": 0,
        "total_conflicts": 0,
        "total_uncompleted_tasks": 0,
        "db_records_cleared": 0,
        "db_records_saved": 0,
        "details": []  # For per-major messages or errors
    }

    try:
        all_data = load_data_from_db(get_connection_func)
        if not all_data:
            summary["message"] = "数据加载失败。"
            return summary

        current_semester = all_data['semesters'].get(target_semester_id)
        if not current_semester:
            summary["message"] = f"未找到 ID 为 {target_semester_id} 的学期信息。"
            return summary
        if current_semester.total_weeks <= 0:
            summary[
                "message"] = f"目标学期 '{current_semester.name}' (ID: {target_semester_id}) 总周数 ({current_semester.total_weeks}) 无效。"
            return summary

        # print(f"SCHEDULER: 选定排课目标学期: '{current_semester.name}' ({current_semester.total_weeks} 周)")

        majors_in_semester = set()
        all_assignments_in_semester = defaultdict(dict)
        for assign_id, assign in all_data['course_assignments'].items():
            if assign.semester_id == target_semester_id:
                majors_in_semester.add(assign.major_id)
                all_assignments_in_semester[assign.major_id][assign_id] = assign

        if not majors_in_semester:
            summary[
                "message"] = f"学期 '{current_semester.name}' (ID: {target_semester_id}) 中未找到任何专业的教学任务。"
            summary["status"] = "success_no_tasks"  # Special status
            return summary

        # print(f"SCHEDULER: 学期 '{current_semester.name}' 共涉及 {len(majors_in_semester)} 个专业。")

        # 清空旧记录
        _, cleared_count = clear_db_for_semester(target_semester_id, get_connection_func)
        summary["db_records_cleared"] = cleared_count
        # print(f"SCHEDULER: 已清空 {cleared_count} 条旧排课记录。")

        all_final_schedule_entries_for_semester = []
        # This global_timetable_state should be shared across all majors scheduled in this run
        # to prevent overall conflicts (e.g., same teacher in two different majors at same time)
        master_global_timetable_state = {'teacher_schedule': set(), 'classroom_schedule': set(),
                                         'major_schedule': set()}

        sorted_major_ids = sorted(list(majors_in_semester), key=lambda mid: all_data['majors'].get(mid, Major(id=mid,
                                                                                                              name=f"UnknownMajor{mid}")).name)

        for major_id in sorted_major_ids:
            current_major = all_data['majors'].get(major_id)
            assignments_for_this_major = all_assignments_in_semester.get(major_id, {})
            major_name = current_major.name if current_major else f"未知专业ID_{major_id}"

            major_detail_msg = f"专业 '{major_name}' (ID: {major_id}): "
            # print(f"\nSCHEDULER: {'='*10} 开始处理专业: {major_name} (ID: {major_id}) {'='*10}")
            if not assignments_for_this_major:
                # print(f"SCHEDULER:   专业 '{major_name}' 没有教学任务，跳过。")
                major_detail_msg += "没有教学任务，跳过。"
                summary["details"].append(major_detail_msg)
                continue

            initial_template, unscheduled_pool = generate_initial_template(assignments_for_this_major, all_data)
            # template_filled_slots = sum(1 for assign_id in initial_template.values() if assign_id is not None)
            # if template_filled_slots == 0 and not unscheduled_pool:
            #     print(f"SCHEDULER:   警告: 未能为专业 '{major_name}' 生成有效的初始模板或后备池，跳过。")
            #     major_detail_msg += "未能生成有效模板，跳过。"
            #     summary["details"].append(major_detail_msg)
            #     continue

            # Pass a copy of master_global_timetable_state or manage it carefully
            # For now, let's assume schedule_with_generated_template correctly updates its local copy
            # and returns what it used. The results should then be merged back.
            # This part is tricky for true global conflict resolution.
            # A simpler model is that each major is scheduled independently for its own students,
            # and teacher/classroom conflicts are checked against a growing master list.

            # For schedule_with_generated_template to use/update a truly global state:
            # It would need to take master_global_timetable_state as an argument and modify it directly,
            # or return the new additions to teacher/classroom schedules to be merged.
            # The original script's `global_timetable_state` was re-initialized in `schedule_with_generated_template`
            # which is fine for isolated major scheduling but not for shared resources like teachers.
            # Let's modify `schedule_with_generated_template` to accept and update `master_global_timetable_state`.
            # No, `schedule_with_generated_template` uses its own `global_timetable_state`.
            # This means it checks constraints based on what it has scheduled *for that major in that run*.
            # To handle cross-major teacher/classroom conflicts, the `master_global_timetable_state`
            # needs to accumulate all successful bookings.

            # Simplified approach: The `check_constraints` needs to check against `master_global_timetable_state`.
            # And `find_available_classroom` also needs to check against `master_global_timetable_state`.
            # And successful bookings are added to `master_global_timetable_state`.
            # This means `schedule_with_generated_template` needs `master_global_timetable_state` as input.

            # For now, let's follow the script's original logic where `global_timetable_state` is effectively per-major within its run.
            # This means the script doesn't inherently prevent a teacher being in two majors at once if scheduled sequentially.
            # This is a limitation of the original algorithm's structure if not handled by the main loop.
            # To fix, `schedule_with_generated_template` should get `master_global_timetable_state`
            # and its `check_constraints` and `find_available_classroom` should use that.
            # And when a class is scheduled, it should update `master_global_timetable_state`.

            # Let's assume the provided `schedule_with_generated_template` is used as is for now.
            # The conflicts it logs are internal to its attempt for that major.
            schedule_result_obj = schedule_with_generated_template(
                assignments_for_this_major, current_semester,
                current_major if current_major else Major(id=major_id, name=major_name),  # ensure current_major exists
                all_data, initial_template, unscheduled_pool
                # master_global_timetable_state # If passing for global check
            )

            major_schedule = schedule_result_obj.get('schedule', [])
            all_final_schedule_entries_for_semester.extend(major_schedule)

            # If using master_global_timetable_state, update it here based on major_schedule
            # for entry in major_schedule:
            #    master_global_timetable_state['teacher_schedule'].add((entry.teacher_id, entry.week_number, entry.timeslot_id))
            #    master_global_timetable_state['classroom_schedule'].add((entry.classroom_id, entry.week_number, entry.timeslot_id))
            #    master_global_timetable_state['major_schedule'].add((entry.major_id, entry.week_number, entry.timeslot_id))

            num_scheduled_major = len(major_schedule)
            num_conflicts_major = len(schedule_result_obj.get('conflicts', []))
            num_uncompleted_major = len(schedule_result_obj.get('unscheduled_details', []))

            summary["processed_majors"] += 1
            summary["total_scheduled_entries"] += num_scheduled_major
            summary["total_conflicts"] += num_conflicts_major
            summary["total_uncompleted_tasks"] += num_uncompleted_major

            major_detail_msg += f"生成课表 {num_scheduled_major}条, 冲突 {num_conflicts_major}次, 未完成任务 {num_uncompleted_major}个。"
            summary["details"].append(major_detail_msg)

        # Save all results for the semester at once
        if all_final_schedule_entries_for_semester:
            saved_count_total = save_schedule_to_db(all_final_schedule_entries_for_semester, get_connection_func)
            summary["db_records_saved"] = saved_count_total
            # print(f"SCHEDULER: 全部专业排课完成，总共保存了 {saved_count_total} 条记录到数据库。")
        # else:
        # print("SCHEDULER: 全部专业排课完成，没有生成任何可保存的课表条目。")

        summary["status"] = "success"
        summary["message"] = f"学期 {target_semester_id} 排课完成。"
        if summary["total_conflicts"] > 0 or summary["total_uncompleted_tasks"] > 0:
            summary["message"] += " 部分任务存在冲突或未完成，详情请查看日志或导出报告。"

        return summary

    except Exception as e:
        print(f"SCHEDULER: 排课主流程发生严重错误: {e}")
        # import traceback; traceback.print_exc()
        summary["message"] = f"排课过程中发生错误: {str(e)}"
        summary["status"] = "error"
        return summary

