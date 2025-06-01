import os
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import pandas as pd
import io
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# --- Database Configuration ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")  # Replace with your DB user
DB_PASSWORD = os.getenv("DB_PASSWORD", "031104")  # Replace with your DB password


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return None


# --- Helper Function ---
def get_id_from_name(cur, table_name, name_column, name_value, id_column='id', additional_conditions=None):
    """Generic function to get ID from a table by name, with optional additional conditions."""
    query = f"SELECT {id_column} FROM {table_name} WHERE {name_column} = %s"
    params = [name_value]
    if additional_conditions:
        for col, val in additional_conditions.items():
            query += f" AND {col} = %s"
            params.append(val)
    cur.execute(query, tuple(params))
    result = cur.fetchone()
    return result[0] if result else None


# --- API Endpoints ---

@app.route('/api/semesters', methods=['GET'])
def get_semesters():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "Database connection failed"}), 500
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name FROM semesters ORDER BY name DESC;")  # Often latest first
        semesters = cur.fetchall()
        return jsonify(semesters)
    except psycopg2.Error as e:
        print(f"Database error in get_semesters: {e}")
        return jsonify({"message": "Failed to retrieve semesters"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route('/api/course-plans', methods=['GET'])
def get_course_plans():
    semester_id = request.args.get('semester_id', type=int)
    if not semester_id:
        return jsonify({"message": "semester_id is required"}), 400

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "Database connection failed"}), 500
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Join with related tables to get names
        query = """
        SELECT 
            ca.id, 
            ca.semester_id,
            ca.major_id,
            m.name AS major_name,
            ca.course_id,
            c.name AS course_name,
            c.course_type,
            c.total_sessions,
            ca.teacher_id,
            u.username AS teacher_name,
            ca.is_core_course,
            ca.expected_students
        FROM course_assignments ca
        JOIN majors m ON ca.major_id = m.id
        JOIN courses c ON ca.course_id = c.id
        JOIN teachers t ON ca.teacher_id = t.id
        JOIN users u ON t.user_id = u.id
        WHERE ca.semester_id = %s
        ORDER BY m.name, c.name;
        """
        cur.execute(query, (semester_id,))
        plans = cur.fetchall()
        return jsonify(plans)
    except psycopg2.Error as e:
        print(f"Database error in get_course_plans: {e}")
        return jsonify({"message": "Failed to retrieve course plans"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route('/api/course-plans/upload', methods=['POST'])
def upload_course_plans():
    if 'file' not in request.files:
        return jsonify({"message": "Request did not include a file"}), 400

    file = request.files['file']
    semester_id_from_form = request.form.get('semester_id', type=int)

    if file.filename == '':
        return jsonify({"message": "No file selected"}), 400
    if not semester_id_from_form:
        return jsonify({"message": "Missing semester_id parameter"}), 400
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return jsonify({"message": "Unsupported file type. Please upload .xls or .xlsx"}), 400

    conn = None
    cur = None
    processed_rows = 0
    created_courses_count = 0
    updated_courses_count = 0
    inserted_assignments_count = 0
    error_messages = []

    try:
        df = pd.read_excel(file, engine='openpyxl' if file.filename.endswith('.xlsx') else None)
        actual_columns = [col.strip() for col in df.columns]
        df.columns = actual_columns

        expected_excel_columns = [
            '学期名称', '专业名称', '课程名称', '总课时',
            '课程类型', '授课教师姓名', '是否核心课程', '预计学生人数'
        ]
        missing_cols = [col for col in expected_excel_columns if col not in df.columns]
        if missing_cols:
            return jsonify({"message": f"Excel file missing required columns: {', '.join(missing_cols)}"}), 400

        conn = get_db_connection()
        if conn is None: return jsonify({"message": "Database connection failed"}), 500
        cur = conn.cursor()
        conn.autocommit = False

        cur.execute("SELECT name FROM semesters WHERE id = %s", (semester_id_from_form,))
        semester_name_from_db_tuple = cur.fetchone()
        if not semester_name_from_db_tuple:
            conn.rollback()
            return jsonify({"message": f"Selected semester ID {semester_id_from_form} is invalid"}), 400
        semester_name_from_db = semester_name_from_db_tuple[0]

        cur.execute("DELETE FROM course_assignments WHERE semester_id = %s", (semester_id_from_form,))
        deleted_count = cur.rowcount
        app.logger.info(f"Deleted {deleted_count} old course_assignments for semester_id {semester_id_from_form}.")

        course_assignments_to_insert = []

        for index, row in df.iterrows():
            processed_rows += 1
            try:
                excel_semester_name = str(row['学期名称']).strip()
                major_name = str(row['专业名称']).strip()
                course_name = str(row['课程名称']).strip()
                total_sessions = row['总课时']
                course_type = str(row['课程类型']).strip()
                teacher_name = str(row['授课教师姓名']).strip()
                is_core_course_str = str(row['是否核心课程']).strip().lower()
                expected_students = row['预计学生人数']

                if excel_semester_name != semester_name_from_db:
                    error_messages.append(
                        f"Row {index + 2}: Semester name '{excel_semester_name}' does not match selected semester '{semester_name_from_db}'. Skipped.")
                    continue

                major_id = get_id_from_name(cur, 'majors', 'name', major_name)
                if major_id is None:
                    error_messages.append(f"Row {index + 2}: Major '{major_name}' not found. Skipped.")
                    continue

                if pd.isna(total_sessions) or not isinstance(total_sessions, (int, float)) or total_sessions < 0:
                    error_messages.append(
                        f"Row {index + 2}: Invalid total_sessions '{total_sessions}' for course '{course_name}'. Skipped.")
                    continue
                total_sessions = int(total_sessions)

                course_id = get_id_from_name(cur, 'courses', 'name', course_name)
                if course_id is None:
                    cur.execute(
                        "INSERT INTO courses (name, total_sessions, course_type) VALUES (%s, %s, %s) RETURNING id",
                        (course_name, total_sessions, course_type)
                    )
                    course_id = cur.fetchone()[0]
                    created_courses_count += 1
                else:
                    cur.execute(
                        "UPDATE courses SET total_sessions = %s, course_type = %s WHERE id = %s AND (total_sessions != %s OR course_type != %s)",
                        (total_sessions, course_type, course_id, total_sessions, course_type)
                    )
                    if cur.rowcount > 0: updated_courses_count += 1

                user_id = get_id_from_name(cur, 'users', 'username', teacher_name,
                                           additional_conditions={'role': 'Teacher'})
                if user_id is None:
                    error_messages.append(
                        f"Row {index + 2}: Teacher '{teacher_name}' (Role: Teacher) not found in users. Skipped.")
                    continue
                teacher_id = get_id_from_name(cur, 'teachers', 'user_id',
                                              user_id)  # 'id' is the pk of teachers, 'user_id' is fk
                if teacher_id is None:
                    error_messages.append(
                        f"Row {index + 2}: Teacher '{teacher_name}' (User ID: {user_id}) not found in teachers table. Skipped.")
                    continue

                is_core_course = is_core_course_str in ['true', '1', '是', 'yes']

                if pd.isna(expected_students) or not isinstance(expected_students,
                                                                (int, float)) or expected_students < 0:
                    error_messages.append(
                        f"Row {index + 2}: Invalid expected_students '{expected_students}' for course '{course_name}'. Skipped.")
                    continue
                expected_students = int(expected_students)

                course_assignments_to_insert.append(
                    (major_id, course_id, teacher_id, semester_id_from_form, is_core_course, expected_students)
                )
            except Exception as row_error:
                error_messages.append(
                    f"Error processing Excel row {index + 2} ('{course_name}'): {row_error}. Skipped.")
                continue

        if course_assignments_to_insert:
            insert_query_ca = """
            INSERT INTO course_assignments (major_id, course_id, teacher_id, semester_id, is_core_course, expected_students)
            VALUES %s
            """
            execute_values(cur, insert_query_ca, course_assignments_to_insert, page_size=100)
            inserted_assignments_count = len(course_assignments_to_insert)

        conn.commit()

        summary_message = f"File processing complete. Processed {processed_rows} Excel rows.\n"
        summary_message += f"Created new courses: {created_courses_count}.\n"
        summary_message += f"Updated existing course info: {updated_courses_count}.\n"
        summary_message += f"Imported course assignments: {inserted_assignments_count} (overwriting previous data for semester ID {semester_id_from_form}).\n"

        if error_messages:
            summary_message += "\nIssues encountered (some rows may have been skipped):\n" + "\n".join(error_messages)
            return jsonify({"message": summary_message, "status": "partial_success"}), 207
        else:
            return jsonify({"message": summary_message, "status": "success"}), 200

    except pd.errors.EmptyDataError:
        if conn: conn.rollback()
        return jsonify({"message": "Uploaded Excel file is empty or unparseable."}), 400
    except KeyError as ke:
        if conn: conn.rollback()
        return jsonify({"message": f"Excel column name error: {ke}. Ensure correct column names."}), 400
    except psycopg2.Error as db_err:
        if conn: conn.rollback()
        app.logger.error(f"Database operation error during Excel import: {db_err}")
        return jsonify({"message": f"Database operation failed: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Unknown error processing Excel file: {e}", exc_info=True)
        return jsonify({"message": f"An unknown error occurred: {e}"}), 500
    finally:
        if cur: cur.close()
        if conn:
            conn.autocommit = True
            conn.close()


@app.route('/api/course-plans/template', methods=['GET'])
def download_template():
    try:
        output = io.BytesIO()
        # Use xlsxwriter for better control if needed, otherwise default engine is fine for simple templates
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:  # Using 'with' ensures writer is closed
            template_columns = [
                '学期名称', '专业名称', '课程名称', '总课时',
                '课程类型', '授课教师姓名', '是否核心课程', '预计学生人数'
            ]
            df_template = pd.DataFrame(columns=template_columns)

            sample_data = {
                '学期名称': ['例如: 2023-2024学年秋季学期'],
                '专业名称': ['例如: 计算机科学与技术'],
                '课程名称': ['例如: 数据结构'],
                '总课时': [64],
                '课程类型': ['理论课'],
                '授课教师姓名': ['例如: 张三 (用户系统中的教师名)'],
                '是否核心课程': ['是'],  # 或 否, 1/0, TRUE/FALSE
                '预计学生人数': [80]
            }
            df_sample = pd.DataFrame(sample_data)
            # df_template = pd.concat([df_template, df_sample], ignore_index=True) # If you want sample data in the template
            df_template.to_excel(writer, sheet_name='课程计划模板', index=False)

            worksheet = writer.sheets['课程计划模板']
            for idx, col in enumerate(df_template.columns):  # Set column widths
                series = df_template[col] if not df_template.empty else pd.Series([col])  # Use col name if empty
                max_len = max((
                    series.astype(str).map(len).max(),
                    len(str(col))
                )) + 2
                worksheet.set_column(idx, idx, max_len)

        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,  # Flask < 2.3
            download_name='course_plan_template.xlsx'  # Flask < 2.3
            # For Flask >= 2.3, use attachment_filename instead of download_name
        )
    except Exception as e:
        app.logger.error(f"Error generating template: {e}", exc_info=True)
        return jsonify({"message": "Failed to generate template"}), 500


@app.route('/api/course-plans/<int:plan_id>', methods=['DELETE'])
def delete_course_plan(plan_id):
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "Database connection failed"}), 500
        cur = conn.cursor()

        cur.execute("SELECT id FROM course_assignments WHERE id = %s", (plan_id,))
        if cur.fetchone() is None:
            return jsonify({"message": "Course plan not found"}), 404

        cur.execute("DELETE FROM course_assignments WHERE id = %s", (plan_id,))
        conn.commit()

        if cur.rowcount > 0:
            return jsonify({"message": f"Course plan {plan_id} deleted successfully"}), 200
        else:
            return jsonify({"message": "Delete failed, plan might have been already deleted"}), 404

    except psycopg2.Error as db_err:
        if conn: conn.rollback()
        app.logger.error(f"DB error deleting course plan {plan_id}: {db_err}")
        return jsonify({"message": f"Database operation failed: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Error deleting course plan {plan_id}: {e}", exc_info=True)
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route('/api/majors-list', methods=['GET'])
def get_majors_list():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "Database connection failed"}), 500
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name FROM majors ORDER BY name")
        majors = cur.fetchall()
        return jsonify(majors), 200
    except Exception as e:
        app.logger.error(f"Error fetching majors list: {e}", exc_info=True)
        return jsonify({"message": "Failed to retrieve majors list"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route('/api/teachers-list', methods=['GET'])
def get_teachers_list():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "Database connection failed"}), 500
        cur = conn.cursor(cursor_factory=RealDictCursor)
        query = """
        SELECT t.id, u.username AS name
        FROM teachers t
        JOIN users u ON t.user_id = u.id
        WHERE u.role = 'Teacher'
        ORDER BY u.username;
        """
        cur.execute(query)
        teachers = cur.fetchall()
        return jsonify(teachers), 200
    except Exception as e:
        app.logger.error(f"Error fetching teachers list: {e}", exc_info=True)
        return jsonify({"message": "Failed to retrieve teachers list"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route('/api/course-plans', methods=['POST'])  # Manual Add
def add_course_plan():
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body cannot be empty"}), 400

    required_fields = ['semester_id', 'major_id', 'course_name', 'total_sessions',
                       'course_type', 'teacher_id', 'is_core_course', 'expected_students']
    missing = [field for field in required_fields if field not in data or data.get(field) is None]  # Check for None too
    if missing:
        return jsonify({"message": f"Missing required fields: {', '.join(missing)}"}), 400

    course_name = str(data.get('course_name', '')).strip()
    if not course_name: return jsonify({"message": "Course name cannot be empty"}), 400

    try:
        total_sessions = int(data['total_sessions'])
        expected_students = int(data['expected_students'])
        if total_sessions < 0 or expected_students < 0:
            return jsonify({"message": "Total sessions and expected students must be non-negative"}), 400
    except (ValueError, TypeError):
        return jsonify({"message": "Total sessions and expected students must be valid integers"}), 400

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "Database connection failed"}), 500
        cur = conn.cursor()
        conn.autocommit = False

        cur.execute("SELECT id FROM courses WHERE name = %s", (course_name,))
        course_result = cur.fetchone()
        course_id = None

        if course_result:
            course_id = course_result[0]
            cur.execute(
                "UPDATE courses SET total_sessions = %s, course_type = %s WHERE id = %s AND (total_sessions != %s OR course_type != %s)",
                (total_sessions, data['course_type'], course_id, total_sessions, data['course_type'])
            )
        else:
            cur.execute(
                "INSERT INTO courses (name, total_sessions, course_type) VALUES (%s, %s, %s) RETURNING id",
                (course_name, total_sessions, data['course_type'])
            )
            course_id = cur.fetchone()[0]

        insert_query = """
        INSERT INTO course_assignments 
            (major_id, course_id, teacher_id, semester_id, is_core_course, expected_students)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        """
        cur.execute(insert_query, (
            data['major_id'], course_id, data['teacher_id'], data['semester_id'],
            bool(data['is_core_course']), expected_students
        ))
        new_plan_id = cur.fetchone()[0]
        conn.commit()

        return jsonify({
            "message": "Course plan added successfully",
            "plan_id": new_plan_id,
            "course_id": course_id
        }), 201

    except psycopg2.IntegrityError as e:
        if conn: conn.rollback()
        error_detail = str(e).lower()
        msg = f"Database integrity error. Check if selected Major/Teacher/Semester IDs are valid. Detail: {e}"
        app.logger.warning(f"Integrity error adding course plan: {e}")
        return jsonify({"message": msg}), 409
    except psycopg2.Error as db_err:
        if conn: conn.rollback()
        app.logger.error(f"DB error adding course plan: {db_err}")
        return jsonify({"message": f"Database operation failed: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Error adding course plan: {e}", exc_info=True)
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if cur: cur.close()
        if conn:
            conn.autocommit = True
            conn.close()


@app.route('/api/course-plans/<int:plan_id>', methods=['PUT'])  # Manual Edit
def update_course_plan(plan_id):
    data = request.get_json()
    if not data:
        return jsonify({"message": "Request body cannot be empty"}), 400

    # semester_id is usually fixed for an existing assignment, course_id is derived
    required_fields = ['major_id', 'course_name', 'total_sessions', 'course_type',
                       'teacher_id', 'is_core_course', 'expected_students']
    missing = [field for field in required_fields if field not in data or data.get(field) is None]
    if missing:
        return jsonify({"message": f"Missing required fields: {', '.join(missing)}"}), 400

    course_name_new = str(data.get('course_name', '')).strip()
    if not course_name_new: return jsonify({"message": "Course name cannot be empty"}), 400

    try:
        total_sessions = int(data['total_sessions'])
        expected_students = int(data['expected_students'])
        if total_sessions < 0 or expected_students < 0:
            return jsonify({"message": "Total sessions and expected students must be non-negative"}), 400
    except (ValueError, TypeError):
        return jsonify({"message": "Total sessions and expected students must be valid integers"}), 400

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "Database connection failed"}), 500
        cur = conn.cursor()
        conn.autocommit = False

        cur.execute("SELECT course_id FROM course_assignments WHERE id = %s", (plan_id,))
        assignment_data = cur.fetchone()
        if not assignment_data:
            conn.rollback()
            return jsonify({"message": "Course plan to edit not found"}), 404
        original_course_id = assignment_data[0]

        # Update the associated course's details in the 'courses' table
        cur.execute(
            """
            UPDATE courses 
            SET name = %s, total_sessions = %s, course_type = %s 
            WHERE id = %s
            """,  # Removed condition to allow updating even if values are same (simpler)
            (course_name_new, total_sessions, data['course_type'], original_course_id)
        )
        # course_id in course_assignments remains original_course_id

        # Update the 'course_assignments' table
        update_query_ca = """
        UPDATE course_assignments SET
            major_id = %s,
            teacher_id = %s,
            is_core_course = %s,
            expected_students = %s
            -- course_id is not changed here, semester_id is also fixed
        WHERE id = %s;
        """
        cur.execute(update_query_ca, (
            data['major_id'], data['teacher_id'], bool(data['is_core_course']),
            expected_students, plan_id
        ))

        # Check if anything was actually updated (optional, but good for feedback)
        # For simplicity, we assume an update call intends to set the values.
        # if cur.rowcount == 0 and courses_update_rowcount == 0 :
        #     conn.rollback()
        #     return jsonify({"message": "Data unchanged, no update performed"}), 200

        conn.commit()
        return jsonify({"message": f"Course plan {plan_id} updated successfully"}), 200

    except psycopg2.IntegrityError as e:
        if conn: conn.rollback()
        error_detail = str(e).lower()
        msg = f"Database integrity error. Check if selected Major/Teacher IDs are valid. Detail: {e}"
        app.logger.warning(f"Integrity error updating course plan {plan_id}: {e}")
        return jsonify({"message": msg}), 409
    except psycopg2.Error as db_err:
        if conn: conn.rollback()
        app.logger.error(f"DB error updating course plan {plan_id}: {db_err}")
        return jsonify({"message": f"Database operation failed: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Error updating course plan {plan_id}: {e}", exc_info=True)
        return jsonify({"message": f"An error occurred: {e}"}), 500
    finally:
        if cur: cur.close()
        if conn:
            conn.autocommit = True
            conn.close()


if __name__ == '__main__':
    app.run(debug=True, port=5000)
