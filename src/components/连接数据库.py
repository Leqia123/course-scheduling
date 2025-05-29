import psycopg2
#建立数据库连接
con = psycopg2.connect(database="postgres", user="postgres", password="031104", host="localhost", port="5432")
#调用游标对象
cur = con.cursor()
#用cursor中的execute 使用DDL语句创建一个名为 STUDENT 的表,指定表的字段以及字段类型
select_query = """-- 创建 Semesters 表（学期表）
CREATE TABLE Semesters (
    SemesterID SERIAL PRIMARY KEY,
    Name VARCHAR(50) NOT NULL,
    StartDate DATE NOT NULL,
    EndDate DATE NOT NULL
);

-- 创建 Majors 表（专业表）
CREATE TABLE Majors (
    MajorID SERIAL PRIMARY KEY,
    MajorName VARCHAR(100) NOT NULL
);

-- 创建 Courses 表（课程表）
CREATE TABLE Courses (
    CourseID SERIAL PRIMARY KEY,
    CourseName VARCHAR(100) NOT NULL,
    TotalSessions INT NOT NULL
);

-- 创建 Students 表（学生表）
CREATE TABLE Students (
    StudentID INT PRIMARY KEY,
    MajorID INT,
    FOREIGN KEY (StudentID) REFERENCES Users(UserID),
    FOREIGN KEY (MajorID) REFERENCES Majors(MajorID)
);

-- 创建 Teachers 表（教员表）
CREATE TABLE Teachers (
    TeacherID INT PRIMARY KEY,
    FOREIGN KEY (TeacherID) REFERENCES Users(UserID)
);

-- 创建 TeacherCourses 表（教员课程表）
CREATE TABLE TeacherCourses (
    TeacherCourseID SERIAL PRIMARY KEY,
    TeacherID INT,
    CourseID INT,
    FOREIGN KEY (TeacherID) REFERENCES Teachers(TeacherID),
    FOREIGN KEY (CourseID) REFERENCES Courses(CourseID),
    UNIQUE (TeacherID, CourseID)
);

-- 创建 CourseAssignments 表（课程分配表）
CREATE TABLE CourseAssignments (
    AssignmentID SERIAL PRIMARY KEY,
    MajorID INT,
    CourseID INT,
    TeacherID INT,
    SemesterID INT,
    FOREIGN KEY (MajorID) REFERENCES Majors(MajorID),
    FOREIGN KEY (CourseID) REFERENCES Courses(CourseID),
    FOREIGN KEY (TeacherID) REFERENCES Teachers(TeacherID),
    FOREIGN KEY (SemesterID) REFERENCES Semesters(SemesterID),
    UNIQUE (SemesterID, MajorID, CourseID)
);

-- 创建 Classrooms 表（教室表）
CREATE TABLE Classrooms (
    ClassroomID SERIAL PRIMARY KEY,
    Building VARCHAR(50),
    RoomNumber VARCHAR(20)
);

-- 创建 TimeSlots 表（时间段表，简化版）
CREATE TABLE TimeSlots (
    TimeSlotID SERIAL PRIMARY KEY,
    DayOfWeek VARCHAR(10),
    Period INT,
    StartTime TIME,
    EndTime TIME,
    UNIQUE (DayOfWeek, Period)
);

-- 创建 Timetable 表（课表）
CREATE TABLE Timetable (
    TimetableID SERIAL PRIMARY KEY,
    SemesterID INT,
    MajorID INT,
    CourseID INT,
    TeacherID INT,
    ClassroomID INT,
    TimeSlotID INT,
    WeekNumber INT,
    FOREIGN KEY (SemesterID) REFERENCES Semesters(SemesterID),
    FOREIGN KEY (MajorID) REFERENCES Majors(MajorID),
    FOREIGN KEY (CourseID) REFERENCES Courses(CourseID),
    FOREIGN KEY (TeacherID) REFERENCES Teachers(TeacherID),
    FOREIGN KEY (ClassroomID) REFERENCES Classrooms(ClassroomID),
    FOREIGN KEY (TimeSlotID) REFERENCES TimeSlots(TimeSlotID),
    UNIQUE (SemesterID, ClassroomID, TimeSlotID, WeekNumber),
    UNIQUE (SemesterID, TeacherID, TimeSlotID, WeekNumber)
);

-- 创建 AdjustmentApplications 表（调课申请表）
CREATE TABLE AdjustmentApplications (
    ApplicationID SERIAL PRIMARY KEY,
    TeacherID INT,
    TimetableID INT,
    ProposedTimeSlotID INT,
    ProposedWeekNumber INT,
    Status VARCHAR(20) NOT NULL DEFAULT 'Pending',
    Reason TEXT,
    AdminComment TEXT,
    SubmittedAt TIMESTAMP,
    ProcessedAt TIMESTAMP,
    FOREIGN KEY (TeacherID) REFERENCES Teachers(TeacherID),
    FOREIGN KEY (TimetableID) REFERENCES Timetable(TimetableID),
    FOREIGN KEY (ProposedTimeSlotID) REFERENCES TimeSlots(TimeSlotID)
);

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
