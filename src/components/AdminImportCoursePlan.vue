<template>
  <div class="page-content admin-import-course-plan">
    <div class="header-controls">
      <div class="semester-selector">
        <label for="semester-select">学期:</label>
        <select id="semester-select" v-model="selectedSemester" @change="fetchCoursePlans">
          <option value="2019-2020-1">2019-2020-1</option>
          <option value="2019-2020-2">2019-2020-2</option>
          <!-- TODO: 从后端加载学期列表 -->
        </select>
      </div>
      <div class="action-buttons">
        <button class="action-button primary-button" @click="handleManualAdd">手动添加</button>
        <button class="action-button" @click="handleDownloadTemplate">下载模板</button>
        <!-- 实际的文件输入，通过按钮点击触发 -->
        <input type="file" ref="fileInput" style="display: none;" @change="handleImportExcel" accept=".xls,.xlsx" />
        <button class="action-button success-button" @click="triggerFileInput">从Excel导入 <i class="icon-upload"></i></button>
        <button class="action-button success-button" @click="handleUploadToServer">上传到服务器 <i class="icon-server"></i></button>
        <button class="action-button primary-button" @click="handleScheduling">排课 <i class="icon-schedule"></i></button>
      </div>
    </div>

    <p class="upload-hint">
      只能上传xls/xlsx文件，导入新任务后将清空原来的任务，请一次性将本学期课程导入完毕
    </p>

    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th><input type="checkbox" /></th>
            <th>学期</th>
            <th>年级</th>
            <th>班级</th>
            <th>课号</th>
            <th>课名</th>
            <th>课属性</th>
            <th>讲师编号</th>
            <th>讲师</th>
            <th>学生人数</th>
            <th>总学时</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="course in filteredCoursePlans" :key="course.id">
            <td><input type="checkbox" /></td>
            <td>{{ course.semester }}</td>
            <td>{{ course.grade }}</td>
            <td>{{ course.class_id }}</td>
            <td>{{ course.course_code }}</td>
            <td>{{ course.course_name }}</td>
            <td>{{ course.course_property }}</td>
            <td>{{ course.teacher_id }}</td>
            <td>{{ course.teacher_name }}</td>
            <td>{{ course.student_count }}</td>
            <td>{{ course.TotalSessions }}</td>

            <td>
              <button class="button edit-button" @click="handleEditCourse(course)">编辑</button>
              <button class="button delete-button" @click="handleDeleteCourse(course.id)">删除</button>
            </td>
          </tr>
          <tr v-if="filteredCoursePlans.length === 0">
            <td colspan="15" style="text-align: center; color: #666; padding: 20px;">
              当前学期没有课程计划数据。
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 课程计划添加/编辑模态框 -->
    <div v-if="isModalVisible" class="modal-overlay" @click.self="closeCourseModal">
      <div class="modal-content">
        <h3>{{ formMode === 'add' ? '添加新课程计划' : '编辑课程计划' }}</h3>
        <form @submit.prevent="saveCourse">
          <div class="form-group">
            <label for="modal-semester">学期:</label>
            <input id="modal-semester" type="text" v-model="currentCourse.semester" required />
          </div>
          <div class="form-group">
            <label for="modal-grade">年级:</label>
            <input id="modal-grade" type="text" v-model="currentCourse.grade" required />
          </div>
          <div class="form-group">
            <label for="modal-class-id">班级:</label>
            <input id="modal-class-id" type="text" v-model="currentCourse.class_id" required />
          </div>
          <div class="form-group">
            <label for="modal-course-code">课号:</label>
            <input id="modal-course-code" type="text" v-model="currentCourse.course_code" required />
          </div>
          <div class="form-group">
            <label for="modal-course-name">课名:</label>
            <input id="modal-course-name" type="text" v-model="currentCourse.course_name" required />
          </div>
          <div class="form-group">
            <label for="modal-course-property">课属性:</label>
            <input id="modal-course-property" type="text" v-model="currentCourse.course_property" />
          </div>
          <div class="form-group">
            <label for="modal-teacher-id">讲师编号:</label>
            <input id="modal-teacher-id" type="text" v-model="currentCourse.teacher_id" />
          </div>
          <div class="form-group">
            <label for="modal-teacher-name">讲师:</label>
            <input id="modal-teacher-name" type="text" v-model="currentCourse.teacher_name" />
          </div>
          <div class="form-group">
            <label for="modal-student-count">学生人数:</label>
            <input id="modal-student-count" type="number" v-model.number="currentCourse.student_count" />
          </div>
          <div class="form-group">
            <label for="modal-weekly-hours">总学时:</label>
            <input id="modal-weekly-hours" type="number" v-model.number="currentCourse.TotalSessions" />
          </div>



          <div class="modal-actions">
            <button type="submit" class="primary-button">保存</button>
            <button type="button" class="cancel-button" @click="closeCourseModal">取消</button>
          </div>
        </form>
        <p v-if="modalMessage" class="message">{{ modalMessage }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';

const selectedSemester = ref('2019-2020-1'); // 默认选中学期

// 模态框相关
const isModalVisible = ref(false);
const currentCourse = ref({}); // 当前编辑或添加的课程数据
const formMode = ref('add'); // 'add' 或 'edit'
const modalMessage = ref(''); // 模态框内的反馈信息

// 模拟课程计划数据 (包含所有学期的数据，以便模拟切换学期)
const allCoursePlans = ref([
  { id: 1, semester: '2019-2020-1', grade: '01', class_id: '202001', course_code: '100001', course_name: '高一语文必修1', course_property: '01', teacher_id: '10010', teacher_name: '梁晓明', student_count: 42, TotalSessions:32},
  { id: 2, semester: '2019-2020-1', grade: '01', class_id: '202001', course_code: '100033', course_name: '高一数学必修1', course_property: '01', teacher_id: '10012', teacher_name: '李雪雪', student_count: 37,TotalSessions:32},
  { id: 3, semester: '2019-2020-1', grade: '01', class_id: '202001', course_code: '100056', course_name: '高一英语必修1', course_property: '01', teacher_id: '10013', teacher_name: '王小芳', student_count: 39,TotalSessions:32},
  { id: 4, semester: '2019-2020-1', grade: '02', class_id: '100004', course_code: '100004', course_name: '高一物理1', course_property: '02', teacher_id: '10025', teacher_name: '张德良', student_count: 42, TotalSessions:32},
  { id: 5, semester: '2019-2020-1', grade: '02', class_id: '100014', course_code: '100014', course_name: '高一化学必修1', course_property: '02', teacher_id: '10033', teacher_name: '韩云', student_count: 40, TotalSessions:32},
  { id: 6, semester: '2019-2020-1', grade: '02', class_id: '100041', course_code: '100041', course_name: '高一思想政治必修1', course_property: '02', teacher_id: '10045', teacher_name: '江大波', student_count: 40, TotalSessions:32},
  { id: 7, semester: '2019-2020-1', grade: '02', class_id: '100021', course_code: '100021', course_name: '高一历史必修1', course_property: '02', teacher_id: '10044', teacher_name: '吴天盛', student_count: 40, TotalSessions:32},
  { id: 8, semester: '2019-2020-1', grade: '02', class_id: '100007', course_code: '100007', course_name: '高一地理必修1', course_property: '02', teacher_id: '10043', teacher_name: '王杰', student_count: 40, TotalSessions:32},
  { id: 9, semester: '2019-2020-1', grade: '02', class_id: '100027', course_code: '100027', course_name: '高一生物必修1', course_property: '02', teacher_id: '10042', teacher_name: '谭晓燕', student_count: 40, TotalSessions:32},
  { id: 10, semester: '2019-2020-1', grade: '04', class_id: '100051', course_code: '100051', course_name: '体育课', course_property: '04', teacher_id: '10041', teacher_name: '张杰', student_count: 40,TotalSessions:32},
  // 模拟另一个学期的数据
  { id: 11, semester: '2019-2020-2', grade: '01', class_id: '202001', course_code: '100002', course_name: '高一语文必修2', course_property: '01', teacher_id: '10010', teacher_name: '梁晓明', student_count: 40,TotalSessions:32},
  { id: 12, semester: '2019-2020-2', grade: '02', class_id: '100005', course_code: '100005', course_name: '高一物理2', course_property: '02', teacher_id: '10025', teacher_name: '张德良', student_count: 40,TotalSessions:32},
]);

// 根据选中学期过滤课程计划
const filteredCoursePlans = computed(() => {
  return allCoursePlans.value.filter(course => course.semester === selectedSemester.value);
});

// 文件输入引用
const fileInput = ref(null);

onMounted(() => {
  // TODO: 实际应用中，这里应该从后端获取所有学期的课程计划
  // fetchCoursePlans();
});

// ======================= 顶部操作按钮功能 =======================

// 手动添加课程计划
const handleManualAdd = () => {
  formMode.value = 'add';
  currentCourse.value = {
    id: Date.now(), // 简单生成一个唯一ID
    semester: selectedSemester.value, // 默认当前选中学期
    grade: '',
    class_id: '',
    course_code: '',
    course_name: '',
    course_property: '',
    teacher_id: '',
    teacher_name: '',
    student_count: 0,
    weekly_hours: 0,
    weeks: 0,
    fixed: 0,
    time: ''
  };
  isModalVisible.value = true;
  modalMessage.value = '';
};

// 下载模板
const handleDownloadTemplate = () => {
  console.log('模拟下载Excel模板...');
  const csvContent = "学期,年级,班级,课号,课名,课属性,讲师编号,讲师,学生人数,总学时\n";
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  if (link.download !== undefined) { // feature detection
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', '课程计划导入模板.csv'); // 通常模板是CSV或XLSX
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url); // 释放URL对象
  } else {
    alert('您的浏览器不支持直接下载，请右键保存链接内容。');
  }
  modalMessage.value = '模板下载已触发。';
};

// 触发文件选择
const triggerFileInput = () => {
  fileInput.value.click();
};

// 从Excel导入 (模拟功能)
const handleImportExcel = (event) => {
  const file = event.target.files[0];
  if (!file) {
    modalMessage.value = '未选择文件。';
    return;
  }
  if (!file.name.endsWith('.xls') && !file.name.endsWith('.xlsx')) {
    modalMessage.value = '文件格式不正确，请上传xls或xlsx文件。';
    return;
  }

  console.log('模拟从Excel导入文件:', file.name);
  modalMessage.value = `正在模拟导入文件: ${file.name}...`;

  // 实际项目中，这里会使用 FileReader 读取文件内容，然后使用如 `xlsx` 这样的库解析 Excel
  // 或者将文件上传到后端，由后端进行解析。
  // 为了演示，我们假设解析后得到以下新数据：
  setTimeout(() => {
    const importedData = [
      { id: Date.now() + 1, semester: selectedSemester.value, grade: '03', class_id: '20200301', course_code: '200001', course_name: '高二物理必修1', course_property: '01', teacher_id: '10020', teacher_name: '李华', student_count: 35, weekly_hours: 4, weeks: 20, fixed: 0, time: '' },
      { id: Date.now() + 2, semester: selectedSemester.value, grade: '03', class_id: '20200302', course_code: '200002', course_name: '高二化学必修1', course_property: '01', teacher_id: '10021', teacher_name: '赵强', student_count: 38, weekly_hours: 4, weeks: 20, fixed: 0, time: '' },
    ];

    // 清空当前学期的原有任务并添加新导入的任务
    allCoursePlans.value = allCoursePlans.value.filter(c => c.semester !== selectedSemester.value);
    allCoursePlans.value.push(...importedData);

    modalMessage.value = `文件 "${file.name}" 模拟导入成功！已添加 ${importedData.length} 条记录。`;
    // 清空文件输入，以便下次选择相同文件也能触发change事件
    event.target.value = '';
  }, 1500);
};

// 上传到服务器 (模拟功能)
const handleUploadToServer = () => {
  console.log('模拟上传当前课程计划到服务器:', filteredCoursePlans.value);
  modalMessage.value = '正在将当前课程计划上传到服务器...';
  // 实际会通过 axios.post('/api/upload-course-plans', filteredCoursePlans.value) 等方式发送数据
  setTimeout(() => {
    modalMessage.value = '当前课程计划已模拟上传成功！';
  }, 1000);
};

// 触发排课 (模拟功能)
const handleScheduling = () => {
  console.log('模拟触发排课算法，基于当前课程计划和教师/教室资源...');
  modalMessage.value = '正在触发自动排课流程，请稍候...';
  // 实际会通过 axios.post('/api/run-scheduling') 等方式触发后端排课服务
  setTimeout(() => {
    modalMessage.value = '排课流程已模拟启动！请前往“查看课表”确认结果。';
  }, 2000);
};

// ======================= 模态框及表单功能 =======================

// 关闭模态框
const closeCourseModal = () => {
  isModalVisible.value = false;
  modalMessage.value = ''; // 清空模态框消息
};

// 保存课程（添加或编辑）
const saveCourse = () => {
  if (formMode.value === 'add') {
    // 添加新课程
    allCoursePlans.value.push({ ...currentCourse.value });
    modalMessage.value = '课程计划添加成功！';
    console.log('添加新课程:', currentCourse.value);
  } else {
    // 编辑现有课程
    const index = allCoursePlans.value.findIndex(c => c.id === currentCourse.value.id);
    if (index !== -1) {
      allCoursePlans.value[index] = { ...currentCourse.value };
      modalMessage.value = '课程计划更新成功！';
      console.log('更新课程:', currentCourse.value);
    } else {
      modalMessage.value = '更新失败，未找到该课程。';
    }
  }
  // 模拟后端保存，实际会有一个API调用
  setTimeout(() => {
    closeCourseModal();
  }, 800); // 稍作延迟关闭
};

// ======================= 表格行操作功能 =======================

// 编辑课程
const handleEditCourse = (course) => {
  formMode.value = 'edit';
  currentCourse.value = { ...course }; // 深度拷贝，避免直接修改原始数据
  isModalVisible.value = true;
  modalMessage.value = '';
};

// 删除课程
const handleDeleteCourse = (id) => {
  if (confirm('确定要删除这条课程计划吗？')) {
    allCoursePlans.value = allCoursePlans.value.filter(course => course.id !== id);
    console.log('删除课程计划 ID:', id);
    // 模拟后端删除，实际会有一个API调用
    // axios.delete(`/api/course-plans/${id}`).then(() => { /* ... */ });
    alert('课程计划已模拟删除！');
  }
};

// 模拟根据学期加载数据
const fetchCoursePlans = () => {
  console.log(`模拟加载 ${selectedSemester.value} 学期的课程计划...`);
  // 实际这里会发起API请求来获取特定学期的课程数据
  // 例如：axios.get(`/api/course-plans?semester=${selectedSemester.value}`);
};
</script>

<style scoped>
/* 保持原有样式，仅做少量调整和新增模态框样式 */
.page-content {
  padding: 20px;
}

.admin-import-course-plan {
  /* 页面特有样式 */
}

.header-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap; /* 响应式布局，按钮可以换行 */
  gap: 10px; /* 按钮和选择器之间的间距 */
}

.semester-selector label {
  margin-right: 10px;
  font-weight: bold;
}

.semester-selector select {
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 14px;
}

.action-buttons button {
  padding: 8px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  margin-left: 10px;
  transition: background-color 0.3s ease;
}

.action-button {
  background-color: #f0f0f0;
  color: #333;
  border: 1px solid #ccc;
}
.action-button:hover {
  background-color: #e0e0e0;
}

.primary-button {
  background-color: #007bff;
  color: white;
}
.primary-button:hover {
  background-color: #0056b3;
}

.success-button {
  background-color: #28a745;
  color: white;
}
.success-button:hover {
  background-color: #218838;
}

.button.delete-button {
  background-color: #dc3545;
  color: white;
  margin-right: 5px;
}
.button.delete-button:hover {
  background-color: #c82333;
}

.button.edit-button {
  background-color: #17a2b8;
  color: white;
  margin-right: 5px; /* 增加编辑按钮和删除按钮之间的间距 */
}
.button.edit-button:hover {
  background-color: #138496;
}

.upload-hint {
  background-color: #e9f7ef;
  border: 1px solid #d4edda;
  color: #155724;
  padding: 10px 15px;
  border-radius: 4px;
  margin-bottom: 20px;
  font-size: 0.9em;
}

.table-container {
  overflow-x: auto; /* 当表格内容超出时横向滚动 */
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
  background-color: white;
  box-shadow: 0 0 10px rgba(0,0,0,0.05);
  border-radius: 8px;
}

table th,
table td {
  border: 1px solid #ddd;
  padding: 10px 12px;
  text-align: left;
  white-space: nowrap; /* 防止内容换行，保持表格紧凑 */
}

table th {
  background-color: #f2f2f2;
  font-weight: bold;
  color: #333;
}

table tbody tr:nth-child(even) {
  background-color: #f9f9f9;
}

table tbody tr:hover {
  background-color: #f1f1f1;
}

/* 模态框样式 - 与教师界面的模态框样式保持一致，或根据需要调整 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6); /* 半透明黑色背景 */
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000; /* 确保在最上层 */
}

.modal-content {
  background-color: #fff;
  padding: 30px; /* 增加内边距 */
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  max-width: 600px; /* 调整宽度以适应更多字段 */
  width: 90%; /* 响应式宽度 */
  max-height: 90vh; /* 最大高度，防止内容过多溢出 */
  overflow-y: auto; /* 内容过多时允许垂直滚动 */
  position: relative;
}

.modal-content h3 {
  margin-top: 0;
  margin-bottom: 20px;
  text-align: center;
  color: #333;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: bold;
  color: #555;
  font-size: 14px;
}

.form-group input[type="text"],
.form-group input[type="number"] {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
  font-size: 14px;
}

.modal-actions {
  margin-top: 25px;
  text-align: right;
}

.modal-actions button {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 15px;
  margin-left: 10px;
  transition: background-color 0.3s ease;
}

.modal-actions .cancel-button {
  background-color: #6c757d;
  color: white;
}

.modal-actions .cancel-button:hover {
  background-color: #5a6268;
}

.message {
    margin-top: 15px;
    text-align: center;
    font-size: 14px;
    color: green;
}

/* 简单的图标占位符 */
.icon-upload::before { content: '⬆'; margin-left: 5px; }
.icon-server::before { content: '☁'; margin-left: 5px; }
.icon-schedule::before { content: '🗓️'; margin-left: 5px; }
</style>
