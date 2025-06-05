import psycopg2
#建立数据库连接
con = psycopg2.connect(database="postgres", user="postgres", password="031104", host="localhost", port="5432")
#调用游标对象
cur = con.cursor()
#用cursor中的execute 使用DDL语句创建一个名为 STUDENT 的表,指定表的字段以及字段类型
select_query = """-- 假设 user 'leqijia' 的 id 是 1009 (根据你的 users 插入语句)
-- SQL for PostgreSQL

CREATE TABLE teacher_scheduling_preferences (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL, -- 哪个老师提出的要求 (FOREIGN KEY to teachers.id)
    semester_id INTEGER NOT NULL, -- 针对哪个学期 (FOREIGN KEY to semesters.id)
    timeslot_id INTEGER NOT NULL, -- 针对哪个时间段 (FOREIGN KEY to time_slots.id)
    preference_type VARCHAR(50) NOT NULL, -- 偏好类型: 'avoid' (避免), 'prefer' (优先), etc. (当前只用 'avoid')
    reason TEXT, -- 教师提出此要求的原因 (可选)
    status VARCHAR(50) DEFAULT 'pending', -- 状态: 'pending', 'approved', 'rejected', 'applied'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- 添加外键约束
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
    FOREIGN KEY (semester_id) REFERENCES semesters(id) ON DELETE CASCADE,
    FOREIGN KEY (timeslot_id) REFERENCES time_slots(id) ON DELETE CASCADE,

    -- 联合唯一约束，防止同一教师在同一学期同一时段提交重复的偏好类型
    UNIQUE (teacher_id, semester_id, timeslot_id, preference_type)
);

;
"""
cur.execute(select_query)
# records = cur.fetchall()
#
# print("Printing each row")
# for row in records:
#     print("ID =", row[0], )
#     print("Name =", row[1])
#     print("Age =", row[2])
#     print("Position =", row[3], "\n")


#提交更改，增添或者修改数据只会必须要提交才能生效
con.commit()
con.close()
