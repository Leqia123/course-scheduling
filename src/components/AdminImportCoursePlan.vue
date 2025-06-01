<template>
  <div class="course-plan-management">
    <h2>课程计划管理</h2>

    <div class="header-controls">
      <div class="semester-selector">
        <label for="semester-select">选择学期:</label>
        <select id="semester-select" v-model="selectedSemesterId" @change="fetchCoursePlans">
          <option value="" disabled>请选择学期</option>
          <option v-for="semester in semesters" :key="semester.id" :value="semester.id">
            {{ semester.name }}
          </option>
        </select>
      </div>
      <div class="action-buttons">
        <button class="action-button primary-button" @click="handleManualAdd" :disabled="!selectedSemesterId">
          <i class="icon-add"></i> 手动添加
        </button>
        <button class="action-button" @click="handleDownloadTemplate">
          <i class="icon-download"></i> 下载模板
        </button>
        <input type="file" ref="fileInputRef" style="display: none;" @change="handleFileSelected" accept=".xls,.xlsx" />
        <button class="action-button success-button" @click="triggerFileInput" :disabled="!selectedSemesterId || uploadStatus === 'uploading'">
            <i class="icon-upload"></i> {{ uploadStatus === 'uploading' ? '上传中...' : '从Excel导入' }}
        </button>
      </div>
    </div>

    <div v-if="uploadStatus === 'uploading'" class="status-message info">正在导入Excel文件，请稍候...</div>
    <div v-if="successMessage" class="status-message success" v-html="formatMessage(successMessage)"></div>
    <div v-if="errorMessage" class="status-message error" v-html="formatMessage(errorMessage)"></div>

    <p v-if="selectedSemesterId && !loadingStatus && coursePlans.length > 0" class="upload-hint">
      提示: 从Excel导入将<strong style="color: red;">覆盖</strong>当前选定学期的所有课程计划。
      Excel文件应包含列：'学期名称', '专业名称', '课程名称', '总课时', '课程类型', '授课教师姓名', '是否核心课程', '预计学生人数'。
    </p>

    <div v-if="loadingStatus === 'loading'" class="status-message info">正在加载课程计划...</div>

    <div class="table-container" v-if="selectedSemesterId && coursePlans.length > 0">
      <table>
        <thead>
          <tr>
            <th>专业</th>
            <th>课程名称</th>
            <th>课程类型</th>
            <th>总学时</th>
            <th>授课教师</th>
            <th>核心课</th>
            <th>预计人数</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="plan in coursePlans" :key="plan.id">
            <td>{{ plan.major_name }}</td>
            <td>{{ plan.course_name }}</td>
            <td>{{ plan.course_type }}</td>
            <td>{{ plan.total_sessions }}</td>
            <td>{{ plan.teacher_name }}</td>
            <td>{{ plan.is_core_course ? '是' : '否' }}</td>
            <td>{{ plan.expected_students }}</td>
            <td>
              <button class="button-link edit-button" @click="handleEditCourse(plan)">编辑</button>
              <button class="button-link delete-button" @click="handleDeleteCourse(plan.id, plan.course_name)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="selectedSemesterId && !loadingStatus && coursePlans.length === 0 && !errorMessage" class="status-message info">
      当前学期没有课程计划数据。您可以手动添加或从Excel导入。
    </div>
     <div v-if="!selectedSemesterId && !loadingStatus" class="status-message info">
      请先选择一个学期以查看或管理课程计划。
    </div>


    <!-- Modal for Add/Edit Course Plan -->
    <div v-if="isModalOpen" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <h3 class="modal-title">{{ modalMode === 'add' ? '添加新课程计划' : '编辑课程计划' }}</h3>
        <form @submit.prevent="handleSubmitPlan">
          <div class="form-grid">
            <div class="form-group">
              <label for="plan-major">专业: <span class="required">*</span></label>
              <select id="plan-major" v-model="currentPlan.major_id" required>
                <option value="" disabled>请选择专业</option>
                <option v-for="major in majorsList" :key="major.id" :value="major.id">
                  {{ major.name }}
                </option>
              </select>
            </div>

            <div class="form-group">
              <label for="plan-teacher">授课教师: <span class="required">*</span></label>
              <select id="plan-teacher" v-model="currentPlan.teacher_id" required>
                <option value="" disabled>请选择教师</option>
                <option v-for="teacher in teachersList" :key="teacher.id" :value="teacher.id">
                  {{ teacher.name }}
                </option>
              </select>
            </div>

            <div class="form-group">
              <label for="plan-course-name">课程名称: <span class="required">*</span></label>
              <input type="text" id="plan-course-name" v-model.trim="currentPlan.course_name" required />
            </div>

            <div class="form-group">
              <label for="plan-course-type">课程类型:</label>
              <input type="text" id="plan-course-type" v-model.trim="currentPlan.course_type" placeholder="例如: 理论课" />
            </div>

            <div class="form-group">
              <label for="plan-total-sessions">总课时: <span class="required">*</span></label>
              <input type="number" id="plan-total-sessions" v-model.number="currentPlan.total_sessions" required min="0" />
            </div>

            <div class="form-group">
              <label for="plan-expected-students">预计学生人数: <span class="required">*</span></label>
              <input type="number" id="plan-expected-students" v-model.number="currentPlan.expected_students" required min="0" />
            </div>

            <div class="form-group checkbox-group full-width">
              <input type="checkbox" id="plan-is-core" v-model="currentPlan.is_core_course" />
              <label for="plan-is-core">是否核心课程</label>
            </div>
          </div>

          <div v-if="modalErrorMessage" class="status-message error modal-error">{{ modalErrorMessage }}</div>

          <div class="modal-actions">
            <button type="button" class="button cancel-button" @click="closeModal" :disabled="isSubmittingModal">取消</button>
            <button type="submit" class="button success-button" :disabled="isSubmittingModal">
              {{ isSubmittingModal ? '提交中...' : (modalMode === 'add' ? '添加计划' : '保存更改') }}
            </button>
          </div>
        </form>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import axios from 'axios';

// --- Configuration ---
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';


// --- State ---
const semesters = ref([]);
const selectedSemesterId = ref('');
const coursePlans = ref([]);
const fileInputRef = ref(null); // Changed name to avoid conflict
// const selectedFile = ref(null); // Not strictly needed if processed immediately

// --- Status Flags ---
const loadingStatus = ref(''); // 'loading', ''
const errorMessage = ref('');
const successMessage = ref('');
const uploadStatus = ref(''); // 'uploading', 'success', 'error', ''

// --- Modal State ---
const isModalOpen = ref(false);
const modalMode = ref('add'); // 'add' or 'edit'
const currentPlan = ref({ // Initialize with all fields for reactivity
  semester_id: '',
  major_id: '',
  course_name: '',
  total_sessions: null,
  course_type: '理论课', // Default
  teacher_id: '',
  is_core_course: false,
  expected_students: null,
});
const editingPlanId = ref(null); // Stores course_assignments.id for editing
// const editingOriginalCourseId = ref(null); // Not strictly needed for current backend PUT
const majorsList = ref([]);
const teachersList = ref([]);
const modalErrorMessage = ref('');
const isSubmittingModal = ref(false);


// --- Lifecycle Hooks ---
onMounted(async () => {
  await fetchSemesters();
  // Initial fetch of dropdown data for modal, can be moved to openModal if preferred
  await fetchModalDropdownData();
});

watch(selectedSemesterId, (newVal, oldVal) => {
  if (newVal && newVal !== oldVal) {
    clearMainMessages();
    coursePlans.value = []; // Clear plans immediately
    fetchCoursePlans(); // Auto-fetch when semester changes and is valid
  } else if (!newVal) {
    coursePlans.value = []; // Clear plans if semester is deselected
    clearMainMessages();
  }
});

// --- Methods ---
const clearMainMessages = () => {
    errorMessage.value = '';
    successMessage.value = '';
    // uploadStatus is handled separately
};

const formatMessage = (message) => {
    // Replace newlines with <br> for HTML display
    return message.replace(/\n/g, '<br>');
};

const fetchSemesters = async () => {
  loadingStatus.value = 'loading';
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    semesters.value = response.data;
    // If there's a previously selected semester or only one semester, select it?
    // For now, requires manual selection.
  } catch (error) {
    console.error('获取学期列表失败:', error);
    errorMessage.value = `获取学期列表失败: ${error.response?.data?.message || error.message}`;
  } finally {
    loadingStatus.value = '';
  }
};

const fetchCoursePlans = async () => {
  if (!selectedSemesterId.value) {
    coursePlans.value = [];
    return;
  }
  loadingStatus.value = 'loading';
  clearMainMessages();
  try {
    const response = await axios.get(`${API_BASE_URL}/api/course-plans`, {
      params: { semester_id: selectedSemesterId.value }
    });
    coursePlans.value = response.data;
  } catch (error) {
    console.error('获取课程计划失败:', error);
    coursePlans.value = []; // Clear on error
    errorMessage.value = `获取课程计划失败: ${error.response?.data?.message || error.message}`;
  } finally {
    loadingStatus.value = '';
  }
};

const triggerFileInput = () => {
  clearMainMessages();
  uploadStatus.value = ''; // Reset upload status
  fileInputRef.value.click();
};

const handleFileSelected = (event) => {
  const file = event.target.files[0];
  if (file) {
    handleImportExcel(file);
  }
  fileInputRef.value.value = ''; // Reset file input
};

const handleImportExcel = async (file) => {
  if (!selectedSemesterId.value) {
    errorMessage.value = '请先选择一个学期才能导入课程计划。';
    return;
  }
  clearMainMessages();
  uploadStatus.value = 'uploading';

  const formData = new FormData();
  formData.append('file', file);
  formData.append('semester_id', selectedSemesterId.value);

  try {
    const response = await axios.post(`${API_BASE_URL}/api/course-plans/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    successMessage.value = response.data.message || 'Excel文件导入成功！';
    uploadStatus.value = 'success';
    await fetchCoursePlans(); // Refresh list
  } catch (error) {
    console.error('Excel导入失败:', error);
    errorMessage.value = `Excel导入失败: ${error.response?.data?.message || '未知错误，请检查文件格式或联系管理员。'}`;
    uploadStatus.value = 'error';
  } finally {
     if (uploadStatus.value === 'uploading') uploadStatus.value = ''; // Reset if still uploading (e.g. network error)
  }
};

const handleDownloadTemplate = async () => {
  clearMainMessages();
  try {
    const response = await axios.get(`${API_BASE_URL}/api/course-plans/template`, {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    const contentDisposition = response.headers['content-disposition'];
    let fileName = 'course_plan_template.xlsx';
    if (contentDisposition) {
        const fileNameMatch = contentDisposition.match(/filename="?(.+)"?/i);
        if (fileNameMatch && fileNameMatch.length === 2) fileName = fileNameMatch[1];
    }
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    successMessage.value = '课程计划模板已开始下载。';
  } catch (error) {
    console.error('下载模板失败:', error);
    errorMessage.value = `下载模板失败: ${error.response?.data?.message || error.message}`;
  }
};

const handleDeleteCourse = async (planId, courseName) => {
  if (!window.confirm(`确定要删除课程计划 “${courseName}” (ID: ${planId}) 吗？此操作不可恢复。`)) {
    return;
  }
  clearMainMessages();
  try {
    await axios.delete(`${API_BASE_URL}/api/course-plans/${planId}`);
    successMessage.value = `课程计划 “${courseName}” (ID: ${planId}) 已成功删除！`;
    await fetchCoursePlans();
  } catch (error) {
    console.error(`删除课程计划 ${planId} 失败:`, error);
    errorMessage.value = `删除失败: ${error.response?.data?.message || error.message}`;
  }
};

const fetchModalDropdownData = async () => {
    // This can be called onMounted or when opening modal for the first time
    if (majorsList.value.length > 0 && teachersList.value.length > 0) return; // Already loaded

    isSubmittingModal.value = true; // Use to indicate loading for dropdowns
    modalErrorMessage.value = '';
    try {
        const [majorsRes, teachersRes] = await Promise.all([
            axios.get(`${API_BASE_URL}/api/majors-list`),
            axios.get(`${API_BASE_URL}/api/teachers-list`)
        ]);
        majorsList.value = majorsRes.data;
        teachersList.value = teachersRes.data;
    } catch (error) {
        console.error('加载专业/教师列表失败:', error);
        // Show error in modal or main page
        modalErrorMessage.value = '加载专业或教师列表失败，请稍后重试或检查网络连接。';
    } finally {
        isSubmittingModal.value = false;
    }
};

const openModal = async (mode, plan = null) => {
  modalMode.value = mode;
  modalErrorMessage.value = '';
  isSubmittingModal.value = false;

  // Ensure dropdown data is available
  if (majorsList.value.length === 0 || teachersList.value.length === 0) {
      await fetchModalDropdownData();
      if (modalErrorMessage.value && (majorsList.value.length === 0 || teachersList.value.length === 0)) {
          // If fetching critical data failed, don't open modal and show main error
          errorMessage.value = modalErrorMessage.value || '无法打开表单：缺少必要数据。';
          isModalOpen.value = false;
          return;
      }
  }

  if (mode === 'add') {
    currentPlan.value = {
      semester_id: selectedSemesterId.value, // Auto-set current semester
      major_id: '',
      course_name: '',
      total_sessions: null,
      course_type: '理论课',
      teacher_id: '',
      is_core_course: false,
      expected_students: null,
    };
    editingPlanId.value = null;
  } else if (mode === 'edit' && plan) {
    currentPlan.value = {
      semester_id: plan.semester_id, // Keep existing semester_id
      major_id: plan.major_id,
      teacher_id: plan.teacher_id,
      course_name: plan.course_name,
      total_sessions: plan.total_sessions,
      course_type: plan.course_type,
      is_core_course: plan.is_core_course,
      expected_students: plan.expected_students,
    };
    editingPlanId.value = plan.id; // This is course_assignments.id
  }
  isModalOpen.value = true;
};

const closeModal = () => {
  isModalOpen.value = false;
  // Reset currentPlan carefully if fields are bound directly
   currentPlan.value = { semester_id: '', major_id: '', course_name: '', total_sessions: null, course_type: '理论课', teacher_id: '', is_core_course: false, expected_students: null, };
  editingPlanId.value = null;
  modalErrorMessage.value = '';
};

const handleManualAdd = () => {
  if (!selectedSemesterId.value) {
    errorMessage.value = '请先选择一个学期才能添加课程计划。';
    return;
  }
  openModal('add');
};

const handleEditCourse = (plan) => {
  openModal('edit', plan);
};

const handleSubmitPlan = async () => {
  modalErrorMessage.value = '';
  isSubmittingModal.value = true;

  const payload = { ...currentPlan.value };
  // Ensure numeric fields are numbers, not strings from input type="number"
  payload.total_sessions = Number(payload.total_sessions);
  payload.expected_students = Number(payload.expected_students);


  // Basic client-side validation (backend will also validate)
  if (!payload.major_id || !payload.course_name || !payload.teacher_id ||
      payload.total_sessions === null || payload.total_sessions < 0 ||
      payload.expected_students === null || payload.expected_students < 0 ) {
      modalErrorMessage.value = '请填写所有必填项 (*)，并确保数值非负。';
      isSubmittingModal.value = false;
      return;
  }
  if (!payload.semester_id && modalMode.value === 'add') { // semester_id must be present for add
     payload.semester_id = selectedSemesterId.value; // re-ensure
     if(!payload.semester_id) {
        modalErrorMessage.value = '未指定学期，无法添加。';
        isSubmittingModal.value = false;
        return;
     }
  }


  try {
    clearMainMessages(); // Clear main page messages before new action
    if (modalMode.value === 'add') {
      await axios.post(`${API_BASE_URL}/api/course-plans`, payload);
      successMessage.value = '新课程计划添加成功！';
    } else { // 'edit'
      await axios.put(`${API_BASE_URL}/api/course-plans/${editingPlanId.value}`, payload);
      successMessage.value = `课程计划 (ID: ${editingPlanId.value}) 更新成功！`;
    }
    closeModal();
    await fetchCoursePlans(); // Refresh the list
  } catch (error) {
    console.error('保存课程计划失败:', error);
    modalErrorMessage.value = `保存失败: ${error.response?.data?.message || error.message}`;
  } finally {
    isSubmittingModal.value = false;
  }
};

</script>

<style scoped>
.course-plan-management {
  padding: 20px;
  font-family: Arial, sans-serif;
  max-width: 1200px;
  margin: auto;
}

h2 {
  text-align: center;
  color: #333;
  margin-bottom: 25px;
}

.header-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.semester-selector {
  display: flex;
  align-items: center;
}
.semester-selector label {
  margin-right: 10px;
  font-weight: bold;
}
.semester-selector select {
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid #ced4da;
  min-width: 200px;
}

.action-buttons button {
  margin-left: 10px;
  padding: 8px 15px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  font-size: 0.9em;
  transition: background-color 0.2s ease;
}
.action-button {
  display: inline-flex;
  align-items: center;
}
.action-button i {
  margin-right: 6px;
}

.primary-button { background-color: #007bff; color: white; }
.primary-button:hover:not(:disabled) { background-color: #0056b3; }
.success-button { background-color: #28a745; color: white; }
.success-button:hover:not(:disabled) { background-color: #1e7e34; }
.action-button:disabled {
  background-color: #cccccc;
  color: #666666;
  cursor: not-allowed;
}


.upload-hint {
  font-size: 0.9em;
  color: #666;
  margin-bottom: 15px;
  padding: 10px;
  background-color: #e9ecef;
  border-left: 3px solid #007bff;
  border-radius: 4px;
}

.status-message {
  padding: 12px 18px;
  margin-bottom: 15px;
  border-radius: 5px;
  font-size: 0.95em;
  border: 1px solid transparent;
}
.status-message.info { background-color: #e6f7ff; border-color: #91d5ff; color: #005280; }
.status-message.success { background-color: #e6ffed; border-color: #b7eb8f; color: #135200; }
.status-message.error { background-color: #fff1f0; border-color: #ffa39e; color: #a8071a; }


.table-container {
  margin-top: 20px;
  overflow-x: auto; /* For responsive tables on small screens */
}
table {
  width: 100%;
  border-collapse: collapse;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
th, td {
  border: 1px solid #dee2e6;
  padding: 10px 12px;
  text-align: left;
  font-size: 0.9em;
}
th {
  background-color: #f2f2f2;
  font-weight: bold;
  color: #333;
}
tbody tr:nth-child(even) {
  background-color: #f9f9f9;
}
tbody tr:hover {
  background-color: #e9ecef;
}

.button-link {
  background: none;
  border: none;
  padding: 0;
  font-family: inherit;
  font-size: inherit;
  cursor: pointer;
  text-decoration: underline;
  margin-right: 10px;
}
.edit-button { color: #007bff; }
.edit-button:hover { color: #0056b3; }
.delete-button { color: #dc3545; }
.delete-button:hover { color: #a71d2a; }


/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 15px; /* For small screens, so modal doesn't touch edges */
}

.modal-content {
  background-color: white;
  padding: 25px 30px;
  border-radius: 8px;
  box-shadow: 0 5px 15px rgba(0,0,0,0.3);
  width: 100%;
  max-width: 650px; /* Wider modal for more fields */
  max-height: 90vh;
  overflow-y: auto;
}

.modal-title {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 1.4em;
  color: #333;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); /* Responsive grid */
  gap: 15px 20px; /* Row gap, Column gap */
}

.form-group {
  /* Removed margin-bottom as gap is handled by grid */
}
.form-group.full-width {
  grid-column: 1 / -1; /* Span full width */
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: bold;
  font-size: 0.9em;
  color: #555;
}
.required { color: red; margin-left: 2px; }

.form-group input[type="text"],
.form-group input[type="number"],
.form-group select {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
  font-size: 1em;
}
.form-group input[type="text"]:focus,
.form-group input[type="number"]:focus,
.form-group select:focus {
  border-color: #007bff;
  outline: none;
  box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25);
}

.form-group.checkbox-group {
  display: flex;
  align-items: center;
  padding-top: 10px; /* Align with other labels if they have margin-bottom */
}
.form-group.checkbox-group input[type="checkbox"] {
  margin-right: 8px;
  width: auto;
  height: auto; /* Use browser default */
  vertical-align: middle;
  transform: scale(1.1);
}
.form-group.checkbox-group label {
  margin-bottom: 0;
  font-weight: normal;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 25px;
  padding-top: 15px;
  border-top: 1px solid #eee;
}
.modal-actions .button {
  padding: 10px 20px;
  margin-left: 10px;
}
.modal-actions .cancel-button {
  background-color: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.modal-actions .cancel-button:hover:not(:disabled) { background-color: #545b62; }


.status-message.modal-error {
    margin-top: 15px;
    margin-bottom: 0;
    grid-column: 1 / -1; /* Span full width if inside grid */
}

/* Icons (simple text based, replace with actual icon font/svg if available) */
.icon-add::before { content: '➕'; }
.icon-download::before { content: '📄'; }
.icon-upload::before { content: '📤'; }
</style>
