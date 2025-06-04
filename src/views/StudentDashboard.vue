<template>
  <div class="student-container timetable-view"> <!-- 添加 timetable-view 类以便复用样式 -->
    <h2>学生课表</h2>
    <!-- 显示欢迎信息 -->
    <p>欢迎您，{{ loggedInUsername }}！</p>
     <div v-if="!loggedInUserId" class="status-message error">
         未能获取您的学生信息（学生ID或专业链接）。请联系管理员或重新登录。
     </div>


    <!-- 课表查询控件 -->
    <!-- 仅在获取到学生ID后显示控件 -->
    <div class="controls" v-if="loggedInUserId">
      <!-- 学期选择 -->
      <div class="control-group">
        <label for="semester-select-student">选择学期:</label>
        <select id="semester-select-student" v-model="selectedSemesterId" @change="onSemesterChange">
          <option value="" disabled>请选择学期</option>
          <option v-for="semester in semesters" :key="semester.id" :value="semester.id">
            {{ semester.name }} {{ semester.total_weeks ? `(共${semester.total_weeks}周)` : '' }}
          </option>
        </select>
      </div>

      <!-- 周数选择 -->
      <div class="control-group">
        <label for="week-select-student">选择周次:</label>
        <select id="week-select-student" v-model="selectedWeek" :disabled="!selectedSemesterId || availableWeeks.length === 0" @change="onWeekChange">
          <option value="" disabled>请选择周次</option>
          <option v-for="week in availableWeeks" :key="week" :value="week">
            第 {{ week }} 周
          </option>
        </select>
      </div>

      <!-- 查询按钮 -->
      <div class="control-group action-group"> <!-- 添加 action-group 类以便样式对齐 -->
        <button @click="fetchStudentTimetable"
                :disabled="!selectedSemesterId || !selectedWeek || isLoading"
                class="button primary-button"> <!-- 使用 AdminStudentTimetable 的按钮样式类 -->
          <i class="icon-search"></i> {{ isLoading ? '查询中...' : '查询课表' }}
        </button>
      </div>

       <!-- 导出按钮 -->
       <div class="control-group action-group">
          <!-- Note: This button exports the *full semester* timetable for the student's major -->
          <button @click="exportStudentTimetable"
                  :disabled="!selectedSemesterId || isLoadingExport"
                  class="button success-button">
            <i class="icon-download"></i> {{ isLoadingExport ? '导出中...' : '导出学期Excel' }}
          </button>
       </div>

    </div>

    <!-- 状态和错误信息 -->
    <div v-if="isLoading && loggedInUserId" class="status-message info">正在加载课表...</div>
    <!-- Ensure errorMessage is shown even if student ID is missing -->
    <div v-if="errorMessage" class="status-message error">{{ errorMessage }}</div>


    <!-- 显示课表 -->
    <!-- 使用 TimetableGridDisplay 组件 -->
    <!-- 仅在获取到学生ID且已查询后显示课表区域 -->
    <div v-if="loggedInUserId && !isLoading && hasSearched" class="timetable-display-area"> <!-- 添加 timetable-display-area 类 -->
       <TimetableGridDisplay
           v-if="timetableEntries.length > 0"
           :entries="timetableEntries"
           :totalWeeks="1"
           :actualWeekNumber="Number(selectedWeek)"
           viewType="student"
       />
        <!-- 没有数据的提示 -->
       <div v-else-if="!errorMessage" class="status-message info">
          未查询到您在此学期、第 {{ selectedWeek }} 周的排课数据。
       </div>
    </div>


    <!-- 退出登录按钮 -->
    <button @click="logout">退出登录</button>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import TimetableGridDisplay from './TimetableGridDisplay.vue'; // 引入课表显示组件

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

const router = useRouter();

const loggedInUsername = ref('');
// We need the user_id from the users table, as the backend API uses user_id to find the student
const loggedInUserId = ref(null); // <-- Store user_id
// The student_id from the students table is not strictly needed for the API call,
// but might be useful for display or other student-specific actions.
// Let's rely on user_id for the API call as implemented in backend.

const semesters = ref([]);
const selectedSemesterId = ref('');
const selectedWeek = ref('');
const timetableEntries = ref([]);

const isLoading = ref(false);
const isLoadingExport = ref(false);
const errorMessage = ref('');
const hasSearched = ref(false);

// Computed properties for semesters and weeks (keep the same)
const selectedSemesterData = computed(() => {
    const idToFind = Number(selectedSemesterId.value);
    return semesters.value.find(s => s.id === idToFind);
});

const availableWeeks = computed(() => {
  const total = selectedSemesterData.value?.total_weeks;
  if (total && total > 0) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  return [];
});

// Watcher for semester change (keep the same)
watch(selectedSemesterId, (newVal, oldVal) => {
    if (newVal !== oldVal) {
        selectedWeek.value = ''; // Clear week selection
        clearTimetableAndStatus();
    }
});

// Component mounted
onMounted(async () => {
  // Read user info from localStorage
  loggedInUsername.value = localStorage.getItem('username') || '学生用户';
  const storedUserId = localStorage.getItem('user_id'); // Get user_id from users table
  const storedUserRole = localStorage.getItem('userRole'); // Get userRole

  // Validate user ID and role
  if (storedUserId && storedUserRole && storedUserRole.toLowerCase() === 'student') {
      loggedInUserId.value = Number(storedUserId);
      console.log(`Student Dashboard: User ID ${loggedInUserId.value} (Role: ${storedUserRole}) logged in.`);
  } else {
      // User ID/role not found or not a student - show error and potentially redirect
      errorMessage.value = '未获取到有效的学生登录信息。请尝试重新登录。';
      console.error('Student Dashboard: Invalid or missing user ID/role in localStorage.');
       // Optional: redirect to login
       // router.push('/login');
       return; // Stop further data fetching if user info is missing/invalid
  }

  // Fetch semesters only if loggedInUserId is set
  if (loggedInUserId.value) {
      await fetchSemesters();

      // Optional: Automatically select the first semester and first week after loading
      // if semesters were fetched successfully and nothing is pre-selected.
      if (semesters.value.length > 0 && !selectedSemesterId.value) {
          selectedSemesterId.value = semesters.value[0].id;
          // watch(selectedSemesterId) will clear selectedWeek
          // If you want to auto-select first week:
           if (semesters.value[0].total_weeks > 0) {
               selectedWeek.value = 1;
               // Optional: auto-fetch timetable for the first week
               // await fetchStudentTimetable(); // Uncomment if you want auto-load
           }
      }
  }
});

// Fetch semesters (keep the same)
const fetchSemesters = async () => {
  isLoading.value = true; // Use general loading for initial fetches
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
     // Ensure id and total_weeks are numbers
    semesters.value = response.data.map(s => ({
        ...s,
        id: Number(s.id),
        total_weeks: Number(s.total_weeks) || 0
    }));
    errorMessage.value = ''; // Clear any previous error on successful fetch
  } catch (error) {
    errorMessage.value = '获取学期列表失败。';
    console.error('Error fetching semesters:', error);
  } finally {
      isLoading.value = false;
  }
};


// Clear timetable data and status messages
const clearTimetableAndStatus = () => {
    timetableEntries.value = [];
    errorMessage.value = ''; // Clear error when selections change
    hasSearched.value = false;
};

// Handle selection changes (calls clearTimetableAndStatus)
const onSemesterChange = () => { clearTimetableAndStatus(); };
const onWeekChange = () => { clearTimetableAndStatus(); };


// Fetch student timetable
const fetchStudentTimetable = async () => {
  // Ensure necessary information is available before fetching
  if (loggedInUserId.value === null || !selectedSemesterId.value || !selectedWeek.value) {
      errorMessage.value = '请先选择学期和周次，并确认您的学生信息已加载。';
      return;
  }

  isLoading.value = true;
  errorMessage.value = ''; // Clear previous error
  timetableEntries.value = []; // Clear old data
  hasSearched.value = true; // Mark that a search was attempted

  try {
    // Call the new backend API endpoint using the loggedInUserId
    const response = await axios.get(
      `${API_BASE_URL}/api/timetables/student/${loggedInUserId.value}/semester/${selectedSemesterId.value}`,
      {
        params: {
          week: Number(selectedWeek.value) // Ensure week is sent as a number query param
        }
      }
    );

    timetableEntries.value = Array.isArray(response.data) ? response.data : [];

    console.log(`Student Dashboard: Fetched ${timetableEntries.value.length} entries for week ${selectedWeek.value}.`);
    // Add logging similar to AdminStudentTimetable for debugging data format

  } catch (error) {
    // Check for specific 404 from backend if student not found/linked
    if (error.response && error.response.status === 404) {
        errorMessage.value = error.response.data.message || '未找到您的学生信息或专业关联，无法获取课表。';
    } else {
        errorMessage.value = `获取个人课表失败: ${error.response?.data?.message || error.message}`;
    }
    timetableEntries.value = []; // Clear on error
    console.error('Error fetching student timetable:', error);
  } finally {
    isLoading.value = false;
  }
};

// Export student timetable
const exportStudentTimetable = async () => {
  // Ensure necessary information is available before exporting
  if (loggedInUserId.value === null || !selectedSemesterId.value) {
       errorMessage.value = '请先选择学期，并确认您的学生信息已加载。';
       return;
  }

  isLoadingExport.value = true;
  errorMessage.value = ''; // Clear previous error

  try {
    // Call the new backend export API endpoint for the student and semester
    const response = await axios.get(
      `${API_BASE_URL}/api/timetables/export/student/${loggedInUserId.value}/semester/${selectedSemesterId.value}`,
      { responseType: 'blob' } // Important for downloading files
    );

    // Create a blob from the response data and create a temporary URL
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;

    // Construct filename (backend provides the primary name in headers, but set here too as fallback)
    // You might parse filename from Content-Disposition header if backend sets it
    // For now, let's construct a reasonable name
    const semesterName = semesters.value.find(s => s.id === Number(selectedSemesterId.value))?.name || `Semester_${selectedSemesterId.value}`;
    const filename = `我的课表_${loggedInUsername.value}_${semesterName}_(全学期).xlsx`;

    link.setAttribute('download', filename); // Set the desired filename for download
    document.body.appendChild(link); // Append link to body
    link.click(); // Programmatically click the link to trigger download

    // Clean up
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url); // Release the object URL

    // Success message (optional)
    // errorMessage.value = '课表导出成功！'; // Or use a success message indicator


  } catch (error) {
    // Check for specific 404 from backend if student not found/linked or no data
    if (error.response && error.response.status === 404) {
        errorMessage.value = error.response.data.message || '未找到该学期的个人排课数据可供导出。';
    } else {
        errorMessage.value = `导出Excel失败: ${error.response?.data?.message || error.message}`;
    }
    console.error('Error exporting student timetable:', error);
  } finally {
    isLoadingExport.value = false;
  }
};


// Logout
const logout = () => {
  // Clear user info from localStorage
  localStorage.removeItem('token');
  localStorage.removeItem('userRole');
  localStorage.removeItem('username');
  localStorage.removeItem('user_id'); // <-- Clear user_id
  // localStorage.removeItem('student_id'); // Remove if you were storing student_id table ID
  // localStorage.removeItem('major_id'); // Remove if you were storing major_id

  // Redirect to login page
  router.push('/login');
};
</script>

<style scoped>
/* 复用 AdminStudentTimetable 的样式 */
.timetable-view {
  padding: 20px;
  max-width: 1200px;
  margin: auto;
}

h2 {
  text-align: center;
  margin-bottom: 20px;
}

/* Adjust controls layout for fewer selectors */
.controls {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
  align-items: flex-end;
  flex-wrap: wrap;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

/* Adjust control-group flex basis as needed */
.control-group {
  display: flex;
  flex-direction: column;
  flex: 1 1 180px; /* Adjust width */
  margin-bottom: 10px;
}

.control-group label {
  margin-bottom: 5px;
  font-weight: bold;
  font-size: 0.9em;
}

.control-group select {
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid #ced4da;
  width: 100%;
  height: 38px;
  box-sizing: border-box;
}

.action-group {
  display: flex;
  align-items: flex-end;
  flex: 0 1 auto; /* Shrink to fit content */
}

.button {
  padding: 8px 15px;
  height: 38px;
  cursor: pointer;
  border: none;
  color: white;
  display: inline-flex;
  align-items: center;
  border-radius: 4px;
  box-sizing: border-box;
  white-space: nowrap;
  margin-right: 5px; /* Spacing between buttons */
}
.button:last-child {
    margin-right: 0;
}


.button i {
  margin-right: 6px;
}

.primary-button {
  background-color: #007bff;
}

.primary-button:hover:not(:disabled) {
  background-color: #0056b3;
}

.success-button {
  background-color: #28a745;
}

.success-button:hover:not(:disabled) {
  background-color: #1e7e34;
}

.button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.status-message {
  padding: 10px;
  margin-top: 15px;
  border-radius: 4px;
}

.info {
  background-color: #e6f7ff;
  border: 1px solid #91d5ff;
  color: #005280;
}

.error {
  background-color: #fff1f0;
  border: 1px solid #ffa39e;
  color: #a8071a;
}

.timetable-display-area {
  margin-top: 20px;
}

/* Icons (already defined in AdminStudentTimetable, just ensure they are here or global) */
.icon-search::before { content: '🔍'; }
.icon-download::before { content: '📄'; }


/* Logout button style */
.student-container > button { /* Use > to target the direct child button */
    margin-top: 20px;
    padding: 10px 15px;
    background-color: #f44336;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}
.student-container > button:hover {
    background-color: #d32f2f;
}
</style>
