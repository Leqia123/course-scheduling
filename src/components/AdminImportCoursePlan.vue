<template>
  <div class="page-content admin-import-course-plan">
    <div class="header-controls">
      <div class="semester-selector">
        <label for="semester-select">学期:</label>
        <select id="semester-select" v-model="selectedSemesterId" @change="fetchCoursePlans">
          <option value="" disabled>请选择学期</option>
          <!-- 动态加载学期 -->
          <option v-for="semester in semesters" :key="semester.id" :value="semester.id">
            {{ semester.name }}
          </option>
        </select>
      </div>
      <div class="action-buttons">
<!--         <button class="action-button primary-button" @click="handleManualAdd">手动添加</button> -->
<!--         <button class="action-button" @click="handleDownloadTemplate">下载模板</button> -->
<!--         实际的文件输入，通过按钮点击触发 -->
        <input type="file" ref="fileInput" style="display: none;" @change="handleFileSelected" accept=".xls,.xlsx" />
        <button class="action-button success-button" @click="triggerFileInput" :disabled="!selectedSemesterId">
            <i class="icon-upload"></i> {{ uploadStatus === 'uploading' ? '上传中...' : '从Excel导入' }}
        </button>
        <!-- 上传到服务器和排课按钮暂时保持模拟或后续实现 -->
        <!-- <button class="action-button success-button" @click="handleUploadToServer">上传到服务器 <i class="icon-server"></i></button> -->
        <!-- <button class="action-button primary-button" @click="handleScheduling">排课 <i class="icon-schedule"></i></button> -->
      </div>
    </div>

    <p class="upload-hint">
      选择学期后，可从Excel导入课程计划。导入新计划将**覆盖**该学期所有原有计划。
      请确保Excel文件包含以下列：<br>
      '学期名称', '专业名称', '课程名称', '总课时', '课程类型', '授课教师姓名', '是否核心课程', '预计学生人数'。<br>
      注意：'学期名称'应与上方所选学期匹配（或用于校验），其他字段将用于更新或创建课程及教学任务。
    </p>


    <!-- 显示加载状态或错误信息 -->
    <div v-if="loadingStatus" class="status-message loading">{{ loadingStatus }}</div>
    <div v-if="errorMessage" class="status-message error">{{ errorMessage }}</div>
    <div v-if="successMessage" class="status-message success">{{ successMessage }}</div>


    <div class="table-container">
      <table>
        <thead>
          <tr>
            <!-- <th><input type="checkbox" /></th> -->
            <th>专业</th>
            <th>课程名称</th>
            <th>课程类型</th>
            <th>教师</th>
            <th>预计人数</th>
            <th>核心课</th>
            <th>总学时</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <!-- 使用从后端获取的 coursePlans 数据 -->
          <tr v-for="plan in coursePlans" :key="plan.id">
            <!-- <td><input type="checkbox" /></td> -->
            <td>{{ plan.major_name }} (ID: {{ plan.major_id }})</td>
            <td>{{ plan.course_name }} (ID: {{ plan.course_id }})</td>
            <td>{{ plan.course_type }}</td>
            <td>{{ plan.teacher_name }} (ID: {{ plan.teacher_id }})</td>
            <td>{{ plan.expected_students }}</td>
            <td>{{ plan.is_core_course ? '是' : '否' }}</td>
            <td>{{ plan.total_sessions }}</td>
            <td>
              <!-- 编辑和删除按钮暂时禁用或后续实现 -->
              <!-- <button class="button edit-button" @click="handleEditCourse(plan)" disabled>编辑</button> -->
              <!-- <button class="button delete-button" @click="handleDeleteCourse(plan.id)" disabled>删除</button> -->
               <span style="color: #999;">N/A</span>
            </td>
          </tr>
          <tr v-if="!loadingStatus && coursePlans.length === 0 && selectedSemesterId">
            <td colspan="8" style="text-align: center; color: #666; padding: 20px;">
              当前学期没有课程计划数据。
            </td>
          </tr>
          <tr v-if="!selectedSemesterId">
            <td colspan="8" style="text-align: center; color: #666; padding: 20px;">
              请先选择一个学期。
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 模态框暂时移除，因为添加/编辑功能未对接后端 -->
    <!-- ... 原有的模态框代码 ... -->

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
// 引入 axios
import axios from 'axios';

// --- State ---
const semesters = ref([]); // 学期列表
const selectedSemesterId = ref(''); // 当前选中的学期 ID
const coursePlans = ref([]); // 从后端获取的课程计划列表
const fileInput = ref(null); // 文件输入元素的引用
const selectedFile = ref(null); // 当前选中的文件

// --- Status Flags ---
const loadingStatus = ref(''); // 加载状态提示信息
const errorMessage = ref(''); // 错误消息
const successMessage = ref(''); // 成功消息
const uploadStatus = ref(''); // 上传状态 ('', 'uploading', 'success', 'error')

// 后端 API 地址 (确保与您的Flask运行地址和端口一致)
const API_BASE_URL = 'http://localhost:5000'; // 或者您的Flask服务器地址

// --- Lifecycle Hooks ---
onMounted(async () => {
  await fetchSemesters();
  // 如果有学期数据，默认选中第一个并加载课程计划
  if (semesters.value.length > 0) {
    // selectedSemesterId.value = semesters.value[0].id; // 可选：默认选中第一个
    // await fetchCoursePlans();
  } else {
      errorMessage.value = "未能加载学期列表，请检查后端服务是否运行。";
  }
});

// --- Methods ---

// 清除状态消息
const clearMessages = () => {
    errorMessage.value = '';
    successMessage.value = '';
    loadingStatus.value = '';
    uploadStatus.value = '';
};

// 获取学期列表
const fetchSemesters = async () => {
  clearMessages();
  loadingStatus.value = '正在加载学期列表...';
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    semesters.value = response.data;
  } catch (error) {
    console.error('获取学期列表失败:', error);
    errorMessage.value = `加载学期列表失败: ${error.response?.data?.message || error.message}`;
    semesters.value = []; // 清空以防万一
  } finally {
    loadingStatus.value = ''; // 清除加载提示
  }
};

// 获取选定学期的课程计划
const fetchCoursePlans = async () => {
  if (!selectedSemesterId.value) {
    coursePlans.value = []; // 如果未选择学期，清空列表
    return;
  }
  clearMessages();
  loadingStatus.value = `正在加载学期 ${selectedSemesterId.value} 的课程计划...`;
  coursePlans.value = []; // 先清空

  try {
    const response = await axios.get(`${API_BASE_URL}/api/course-plans`, {
      params: { semester_id: selectedSemesterId.value }
    });
    coursePlans.value = response.data;
    if (coursePlans.value.length === 0) {
        successMessage.value = `学期 ${selectedSemesterId.value} 当前没有课程计划数据。`;
    }
  } catch (error) {
    console.error(`获取课程计划失败 (学期 ${selectedSemesterId.value}):`, error);
    errorMessage.value = `加载课程计划失败: ${error.response?.data?.message || error.message}`;
    coursePlans.value = []; // 清空列表
  } finally {
    loadingStatus.value = '';
  }
};

// 触发文件选择框
const triggerFileInput = () => {
  // 重置状态并清除之前的选择
  selectedFile.value = null;
  if (fileInput.value) {
      fileInput.value.value = ''; // 清空文件输入，确保选择同名文件也能触发 change
      fileInput.value.click();
  }
};

// 处理文件选择事件
const handleFileSelected = (event) => {
  const file = event.target.files[0];
  if (!file) {
    selectedFile.value = null;
    return;
  }
  if (!file.name.endsWith('.xls') && !file.name.endsWith('.xlsx')) {
    clearMessages();
    errorMessage.value = '文件格式不正确，请上传 .xls 或 .xlsx 文件。';
    selectedFile.value = null;
    event.target.value = ''; // 清空选择
    return;
  }
  selectedFile.value = file;
  // 文件选择后立即尝试上传
  handleImportExcel();
};

// 处理Excel导入（实际是上传文件到后端）
const handleImportExcel = async () => {
  if (!selectedFile.value) {
    errorMessage.value = '请先选择一个Excel文件。';
    return;
  }
  if (!selectedSemesterId.value) {
      errorMessage.value = '请先选择要导入的学期。';
      return;
  }

  clearMessages();
  uploadStatus.value = 'uploading'; // 设置上传状态

  const formData = new FormData();
  formData.append('file', selectedFile.value);
  formData.append('semester_id', selectedSemesterId.value);

  try {
    const response = await axios.post(`${API_BASE_URL}/api/course-plans/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    successMessage.value = response.data.message || '文件上传并处理成功！';
    uploadStatus.value = 'success';
    // 上传成功后，刷新课程计划列表
    await fetchCoursePlans();
  } catch (error) {
    console.error('文件上传或处理失败:', error);
    errorMessage.value = `导入失败: ${error.response?.data?.message || error.message}`;
    uploadStatus.value = 'error';
  } finally {
     // 不论成功失败，一段时间后清除上传状态，除非是上传中
     if (uploadStatus.value !== 'uploading') {
          setTimeout(() => {
              if (uploadStatus.value !== 'uploading') { // 再次检查，防止覆盖进行中的上传
                  uploadStatus.value = '';
              }
          }, 3000); // 3秒后清除状态
     }
    // 清空文件引用和输入框值
    selectedFile.value = null;
    if (fileInput.value) {
        fileInput.value.value = '';
    }
  }
};

// --- 其他按钮的占位或待实现方法 ---
// const handleManualAdd = () => { alert('手动添加功能待实现'); };
// const handleDownloadTemplate = () => { alert('下载模板功能待实现'); };
// const handleUploadToServer = () => { alert('上传到服务器功能待实现'); };
// const handleScheduling = () => { alert('排课功能待实现'); };
// const handleEditCourse = (plan) => { alert(`编辑课程 ${plan.id} 功能待实现`); };
// const handleDeleteCourse = (planId) => { alert(`删除课程 ${planId} 功能待实现`); };

</script>

<style scoped>
/* 保持原有样式，添加状态消息样式 */
.page-content {
  padding: 20px;
}
/* ... (复制/保留您原有的<style scoped>内容) ... */

.status-message {
    padding: 10px 15px;
    border-radius: 4px;
    margin-bottom: 15px;
    text-align: center;
    font-weight: bold;
}
.status-message.loading {
    background-color: #e2e3e5;
    color: #383d41;
    border: 1px solid #d6d8db;
}
.status-message.error {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}
.status-message.success {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
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
  min-width: 180px; /* 给下拉框一个最小宽度 */
}

.action-buttons button {
  padding: 8px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  margin-left: 10px;
  transition: background-color 0.3s ease, opacity 0.3s ease;
  display: inline-flex; /* 让图标和文字对齐 */
  align-items: center;
}
.action-buttons button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}
.action-buttons button i {
    margin-right: 5px; /* 图标和文字间距 */
}

.action-button {
  background-color: #f0f0f0;
  color: #333;
  border: 1px solid #ccc;
}
.action-button:hover:not(:disabled) {
  background-color: #e0e0e0;
}

.primary-button {
  background-color: #007bff;
  color: white;
}
.primary-button:hover:not(:disabled) {
  background-color: #0056b3;
}

.success-button {
  background-color: #28a745;
  color: white;
}
.success-button:hover:not(:disabled) {
  background-color: #218838;
}

.button.delete-button {
  background-color: #dc3545;
  color: white;
  margin-right: 5px;
}
.button.delete-button:hover:not(:disabled) {
  background-color: #c82333;
}

.button.edit-button {
  background-color: #17a2b8;
  color: white;
  margin-right: 5px; /* 增加编辑按钮和删除按钮之间的间距 */
}
.button.edit-button:hover:not(:disabled) {
  background-color: #138496;
}

.upload-hint {
  background-color: #fff3cd; /* Use warning color for hint */
  border: 1px solid #ffeeba;
  color: #856404;
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
  font-size: 14px; /* 稍微调整字体大小 */
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

/* 简单的图标占位符 */
.icon-upload::before { content: '⬆'; }
.icon-server::before { content: '☁'; }
.icon-schedule::before { content: '🗓️'; }
</style>
