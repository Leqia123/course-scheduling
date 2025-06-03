<template>
  <div class="timetable-view">
    <h2>查询专业课表</h2>

    <div class="controls">
      <!-- 学期选择 -->
      <div class="control-group">
        <label for="semester-select-major">选择学期:</label>
        <select id="semester-select-major" v-model="selectedSemesterId" @change="handleSemesterChange">
          <option value="" disabled>请选择学期</option>
          <option v-for="semester in semesters" :key="semester.id" :value="semester.id">
            {{ semester.name }} {{ semester.total_weeks ? `(共${semester.total_weeks}周)` : '' }}
          </option>
        </select>
      </div>

      <!-- 专业选择 -->
      <div class="control-group">
        <label for="major-select">选择专业:</label>
        <select id="major-select" v-model="selectedMajorId" @change="handleMajorChange" :disabled="!selectedSemesterId">
          <option value="" disabled>请选择专业</option>
          <option v-for="major in majors" :key="major.id" :value="major.id">
            {{ major.name }}
          </option>
        </select>
      </div>

      <!-- 周数选择 -->
      <div class="control-group">
        <label for="week-select">选择周数:</label>
        <select id="week-select" v-model="selectedWeek" :disabled="!selectedSemesterId || availableWeeks.length === 0" @change="handleWeekChange">
          <option value="" disabled>请选择周数</option>
          <option v-for="week in availableWeeks" :key="week" :value="week">
            第 {{ week }} 周
          </option>
        </select>
      </div>

      <!-- 查询按钮 -->
      <div class="control-group action-group">
        <button @click="fetchMajorTimetable"
                :disabled="!selectedSemesterId || !selectedMajorId || !selectedWeek || isLoading"
                class="button primary-button">
          <i class="icon-search"></i> {{ isLoading ? '查询中...' : '查询课表' }}
        </button>
      </div>

      <!-- 导出按钮 -->
      <div class="control-group action-group">
        <button @click="exportMajorTimetable"
                :disabled="!selectedSemesterId || !selectedMajorId || isLoadingExport"
                class="button success-button">
          <i class="icon-download"></i> {{ isLoadingExport ? '导出中...' : '导出学期Excel' }}
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="status-message info">正在加载课表...</div>
    <div v-if="errorMessage" class="status-message error">{{ errorMessage }}</div>

    <!-- 显示单周课表 -->
    <div v-if="!isLoading && timetableEntries.length > 0" class="timetable-display-area">
      <TimetableGridDisplay
        :entries="timetableEntries"
        viewType="major"
        :totalWeeks="1"
      />
    </div>
    <div v-if="!isLoading && hasSearched && timetableEntries.length === 0 && !errorMessage" class="status-message info">
      未查询到该专业在此学期、此周的排课数据。
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted, computed, watch } from 'vue'; // 引入 watch
import axios from 'axios';
// 假设 TimetableGridDisplay.vue 位于同一目录或正确路径
import TimetableGridDisplay from './TimetableGridDisplay.vue';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

const semesters = ref([]);
const majors = ref([]);
const selectedSemesterId = ref('');
const selectedMajorId = ref('');
const selectedWeek = ref(''); // 新增：选中的周数
const timetableEntries = ref([]);
const isLoading = ref(false);
const isLoadingExport = ref(false);
const errorMessage = ref('');
const hasSearched = ref(false); // 标记是否执行过查询

// 计算属性：获取选中的学期对象，包含 total_weeks
const selectedSemesterData = computed(() => {
    const idToFind = Number(selectedSemesterId.value);
    return semesters.value.find(s => s.id === idToFind);
});

// 计算属性：根据选中的学期计算可用周数列表
const availableWeeks = computed(() => {
  const total = selectedSemesterData.value?.total_weeks;
  if (total && total > 0) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  return [];
});

// 监听学期变化，清空专业、周数和课表
watch(selectedSemesterId, (newVal, oldVal) => {
    if (newVal !== oldVal) {
        selectedMajorId.value = '';
        selectedWeek.value = ''; // 清空周数选择
        clearTimetableAndStatus();
    }
});

// 监听专业变化，清空周数和课表 (可选，看业务逻辑是否需要)
// watch(selectedMajorId, (newVal, oldVal) => {
//     if (newVal !== oldVal) {
//         selectedWeek.value = ''; // 如果切换专业也需要重选周数
//         clearTimetableAndStatus();
//     }
// });

// 挂载时获取基础数据
onMounted(async () => {
  await fetchSemesters();
  await fetchMajors();
});

// 获取学期列表 (包含 total_weeks)
const fetchSemesters = async () => {
  isLoading.value = true;
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    semesters.value = response.data;
    semesters.value.forEach(s => {
        if (s.total_weeks !== undefined && s.total_weeks !== null) {
            s.total_weeks = Number(s.total_weeks);
        } else {
            s.total_weeks = 0;
        }
    });
  } catch (error) {
    errorMessage.value = '获取学期列表失败。';
    console.error(error);
  } finally {
      isLoading.value = false;
  }
};

// 获取专业列表
const fetchMajors = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/majors-list`);
    majors.value = response.data;
  } catch (error) {
    errorMessage.value = '获取专业列表失败。';
    console.error(error);
  }
};

// 清空课表数据和状态信息
const clearTimetableAndStatus = () => {
    timetableEntries.value = [];
    errorMessage.value = '';
    hasSearched.value = false;
};

// 处理选择器变化的函数，用于清空状态
const handleSemesterChange = () => {
    clearTimetableAndStatus();
};

const handleMajorChange = () => {
    clearTimetableAndStatus();
};

const handleWeekChange = () => {
    clearTimetableAndStatus();
};

// 获取指定专业、学期、周数的课表
const fetchMajorTimetable = async () => {
  if (!selectedSemesterId.value || !selectedMajorId.value || !selectedWeek.value) {
      errorMessage.value = '请先选择学期、专业和周数。';
      return;
  }
  isLoading.value = true;
  errorMessage.value = '';
  timetableEntries.value = [];
  hasSearched.value = true;

  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/timetables/major/${selectedMajorId.value}/semester/${selectedSemesterId.value}`,
      {
        params: {
          week: selectedWeek.value
        }
      }
    );
    timetableEntries.value = Array.isArray(response.data) ? response.data : [];
    console.log('AdminStudentTimetable: Raw data received from backend:', JSON.stringify(response.data));
    if (timetableEntries.value.length > 0) {
      const firstEntry = timetableEntries.value[0];
      console.log('AdminStudentTimetable: First entry details:');
      console.log('  - ID:', firstEntry.id);
      console.log('  - Week Number:', firstEntry.week_number, typeof firstEntry.week_number);
      console.log('  - Day of Week:', firstEntry.day_of_week, typeof firstEntry.day_of_week);
      console.log('  - Period:', firstEntry.period, typeof firstEntry.period);
      console.log('  - Course Name:', firstEntry.course_name);
      console.log('  - Teacher Name:', firstEntry.teacher_name);
      console.log('  - Classroom Name:', firstEntry.classroom_name);
      console.log('  - All Keys:', Object.keys(firstEntry));
    } else {
      console.log('AdminStudentTimetable: Received empty data array from backend.');
    }
  } catch (error) {
    errorMessage.value = `获取专业课表失败: ${error.response?.data?.message || error.message}`;
    timetableEntries.value = [];
    console.error(error);
  } finally {
    isLoading.value = false;
  }
};

// 导出专业课表 (当前逻辑是导出整个学期的，保持不变)
const exportMajorTimetable = async () => {
  if (!selectedSemesterId.value || !selectedMajorId.value) return;
  isLoadingExport.value = true;
  errorMessage.value = '';
  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/timetables/export/major/${selectedMajorId.value}/semester/${selectedSemesterId.value}`,
      { responseType: 'blob' }
    );
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    const majorName = majors.value.find(m => m.id === Number(selectedMajorId.value))?.name || 'UnknownMajor';
    const semesterName = semesters.value.find(s => s.id === Number(selectedSemesterId.value))?.name || 'UnknownSemester';
    link.setAttribute('download', `专业课表_${majorName}_${semesterName}_(全学期).xlsx`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    errorMessage.value = `导出Excel失败: ${error.response?.data?.message || error.message}`;
    console.error(error);
  } finally {
    isLoadingExport.value = false;
  }
};
</script>
<style scoped>
.timetable-view {
  padding: 20px;
  max-width: 1200px;
  margin: auto;
}

h2 {
  text-align: center;
  margin-bottom: 20px;
}

.controls {
  display: flex;
  gap: 15px; /* 控件间距 */
  margin-bottom: 15px;
  align-items: flex-end; /* 让按钮和下拉框底部对齐 */
  flex-wrap: wrap; /* 允许换行 */
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.control-group {
  display: flex;
  flex-direction: column;
  flex: 1 1 200px; /* 每个控件组的宽度 */
  margin-bottom: 10px; /* 换行时的垂直间距 */
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
  width: 100%; /* 使下拉框宽度填满控件组 */
  height: 38px; /* 与按钮高度接近 */
  box-sizing: border-box;
}

.action-group {
  display: flex;
  align-items: flex-end; /* 确保按钮底部对齐 */
  flex: 1 1 150px; /* 按钮组的宽度 */
}

.button {
  padding: 8px 15px; /* 调整按钮内边距 */
  height: 38px; /* 保持与下拉框一致 */
  cursor: pointer;
  border: none;
  color: white;
  display: inline-flex;
  align-items: center;
  border-radius: 4px;
  box-sizing: border-box;
  white-space: nowrap; /* 防止按钮文字换行 */
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

.icon-search::before {
  content: '🔍';
}

.icon-download::before {
  content: '📄';
}
</style>
