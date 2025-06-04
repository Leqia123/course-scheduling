import psycopg2
#建立数据库连接
con = psycopg2.connect(database="postgres", user="postgres", password="031104", host="localhost", port="5432")
#调用游标对象
cur = con.cursor()
#用cursor中的execute 使用DDL语句创建一个名为 STUDENT 的表,指定表的字段以及字段类型
select_query = """-- 假设 user 'leqijia' 的 id 是 1009 (根据你的 users 插入语句)
INSERT INTO students (user_id, major_id, student_id_number) VALUES
(1009, 1, 'S20230001'); 
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
