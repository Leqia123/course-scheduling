<template>
  <div class="page-content">
    <h2>我的课表</h2>

    <!-- Controls for selecting Semester and Week -->
    <div class="controls">
      <div class="select-group">
        <label for="semester-select">选择学期:</label>
        <select id="semester-select" v-model="selectedSemesterId" @change="onSemesterChange">
          <option value="" disabled>请选择学期</option>
          <option v-for="semester in semesters" :key="semester.id" :value="semester.id">
            {{ semester.name }}
          </option>
        </select>
      </div>

      <div class="select-group">
        <label for="week-select">选择周次:</label>
        <select id="week-select" v-model="selectedWeek">
          <option value="" disabled>请选择周次</option>
          <option v-for="week in weeks" :key="week" :value="week">
            第 {{ week }} 周
          </option>
        </select>
      </div>

      <button @click="fetchTeacherTimetable" :disabled="!selectedSemesterId || !selectedWeek || isLoading">
        查询课表
      </button>
    </div>

    <!-- Status messages -->
    <div v-if="isLoading" class="status-message loading">加载中...</div>
    <div v-if="errorMessage" class="status-message error">{{ errorMessage }}</div>
    <div v-if="!isLoading && hasSearched && timetableEntries.length === 0" class="status-message info">
       当前学期第 {{ selectedWeek }} 周没有课表信息。
    </div>

    <!-- Timetable Display -->
    <div class="timetable-display-area" v-if="!isLoading && timetableEntries.length > 0">
        <!-- Pass fetched data to the grid display component -->
        <TimetableGridDisplay
           :entries="timetableEntries"
           :actualWeekNumber="Number(selectedWeek)"
           :totalWeeks="selectedSemesterTotalWeeks"
           viewType="teacher"
         />
    </div>

     <div v-if="!loggedInUserId" class="status-message error">
        未能获取您的教师信息（用户ID）。请联系管理员或重新登录。
    </div>

     <div v-if="loggedInUserId && !hasSearched" class="timetable-placeholder">
      <p>请选择学期和周次查询您的课表。</p>
      <p>(选择上方选项后点击查询)</p>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import axios from 'axios';
import TimetableGridDisplay from './TimetableGridDisplay.vue'; // 引入课表展示组件
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'; // 假设你有一个config文件存放API基础URL

// Reactive state variables
const loggedInUserId = ref(null);
const semesters = ref([]);
const selectedSemesterId = ref('');
const selectedSemesterTotalWeeks = ref(0); // Store total weeks for selected semester
const weeks = ref([]); // Array of week numbers for the selected semester
const selectedWeek = ref('');
const timetableEntries = ref([]); // Array to hold fetched timetable data
const isLoading = ref(false);
const errorMessage = ref('');
const hasSearched = ref(false); // To show initial message before search

// Fetch list of semesters from backend
const fetchSemesters = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    semesters.value = response.data;
    // Optional: Auto-select the first semester if list is not empty
    if (semesters.value.length > 0) {
      selectedSemesterId.value = semesters.value[0].id;
    }
  } catch (error) {
    console.error('Error fetching semesters:', error);
    errorMessage.value = '无法加载学期信息。';
  }
};

// Fetch timetable data for the logged-in teacher, selected semester, and week
// In TeacherTimetable.vue

// ... (other imports and ref definitions)

const fetchTeacherTimetable = async () => {
  if (loggedInUserId.value === null) {
      errorMessage.value = '未能获取您的教师用户ID，无法查询课表。请重新登录。';
      return;
  }
  if (!selectedSemesterId.value || !selectedWeek.value) {
      errorMessage.value = '请先选择学期和周次。';
      return;
  }

  isLoading.value = true;
  errorMessage.value = ''; // Clear previous errors
  timetableEntries.value = []; // Clear previous timetable data
  hasSearched.value = true; // Mark that a search attempt has been made

  try {
    // *** MODIFIED API URL ***
    const response = await axios.get(
      // Use the new route specifically for weekly view
      `${API_BASE_URL}/api/timetables/teacher-dashboard/${loggedInUserId.value}/semester/${selectedSemesterId.value}`,
      {
        params: {
          week: Number(selectedWeek.value) // Pass week as a query parameter
        }
      }
    );
    timetableEntries.value = response.data;
    console.log('Teacher Timetable fetched:', timetableEntries.value);

  } catch (error) {
    console.error('Error fetching teacher timetable:', error);
    if (error.response && error.response.status === 404) {
         // Specific handling for 404 if backend sends it when no timetable is found
         errorMessage.value = '该学期该周次没有找到您的课表信息。';
         timetableEntries.value = []; // Ensure array is empty on 404
     } else if (error.response) {
         errorMessage.value = `查询课表失败: ${error.response.data.error || error.response.statusText}`;
     }
     else {
      errorMessage.value = '查询课表时发生网络错误或服务器无响应。';
    }
  } finally {
    isLoading.value = false;
  }
};

// ... (rest of the script)


// Handle semester selection change to populate weeks dropdown
const onSemesterChange = () => {
  const semester = semesters.value.find(s => s.id === selectedSemesterId.value);
  if (semester) {
    selectedSemesterTotalWeeks.value = semester.total_weeks;
    weeks.value = Array.from({ length: semester.total_weeks }, (_, i) => i + 1);
    selectedWeek.value = ''; // Reset selected week when semester changes
  } else {
      selectedSemesterTotalWeeks.value = 0;
      weeks.value = [];
      selectedWeek.value = '';
  }
};

// On component mount
onMounted(async () => {
  // Retrieve logged-in user info from localStorage
   const storedUserId = localStorage.getItem('user_id');
   const storedUserRole = localStorage.getItem('userRole');

   // Validate user ID and role
   if (storedUserId && storedUserRole && storedUserRole.toLowerCase() === 'teacher') {
       loggedInUserId.value = Number(storedUserId);
       console.log(`Teacher Timetable: User ID ${loggedInUserId.value} (Role: ${storedUserRole}) logged in.`);
        // Fetch semesters after confirming user is valid
       await fetchSemesters();
   } else {
       errorMessage.value = '未获取到有效的教师登录信息或您的账号不是教师类型。请尝试重新登录。';
       loggedInUserId.value = null; // Ensure it's null if not a valid teacher
       console.error('Teacher Timetable: Invalid or missing user ID/role in localStorage.');
        // Optional: router.push('/login'); // Uncomment if you want to redirect
   }
});

// Watch for selectedSemesterId changes to update weeks (redundant with onSemesterChange called by @change,
// but can be useful if selectedSemesterId is set programmatically)
watch(selectedSemesterId, (newId) => {
    if (newId) {
         onSemesterChange(); // Call the same logic
     }
});

</script>

<style scoped>
.page-content {
  padding: 20px;
  max-width: 1200px; /* Optional: Limit max width for better readability */
  margin: 0 auto; /* Center the content */
}

h2 {
  text-align: center;
  color: #333;
  margin-bottom: 20px;
}

.controls {
  display: flex;
  gap: 20px; /* Space between control groups */
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap; /* Allow controls to wrap on smaller screens */
}

.select-group {
  display: flex;
  align-items: center;
  gap: 10px; /* Space between label and select */
}

.controls label {
  font-weight: bold;
  color: #555;
}

.controls select,
.controls button {
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 1em;
}

.controls button {
  background-color: #007bff;
  color: white;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.controls button:hover:not(:disabled) {
  background-color: #0056b3;
}

.controls button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}


.status-message {
    margin-top: 15px;
    padding: 10px;
    border-radius: 4px;
    text-align: center;
    font-weight: bold;
}

.loading {
    background-color: #e9d8fd;
    color: #673ab7;
}

.error {
    background-color: #f8d7da;
    color: #721c24;
    border-color: #f5c6cb;
}

.info {
     background-color: #d1ecf1;
     color: #0c5460;
     border-color: #bee5eb;
}


.timetable-display-area {
  margin-top: 20px;
  border: 1px solid #eee; /* Optional border around the grid */
  padding: 10px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  border-radius: 4px;
}

.timetable-placeholder {
  border: 1px dashed #ccc;
  padding: 20px;
  text-align: center;
  margin-top: 20px;
  min-height: 150px; /* Slightly smaller placeholder */
  background-color: #f9f9f9;
  color: #888;
  border-radius: 4px;
}
</style>

