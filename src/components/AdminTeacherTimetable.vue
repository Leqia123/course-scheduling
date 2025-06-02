<template>
  <div class="timetable-view">
    <h2>查询教师课表</h2>

    <div class="controls">
      <div class="control-group">
        <label for="semester-select-teacher">选择学期:</label>
        <select id="semester-select-teacher" v-model="selectedSemesterId" @change="onSemesterChange">
          <option value="" disabled>请选择学期</option>
          <option v-for="semester in semesters" :key="semester.id" :value="semester.id">
            {{ semester.name }}
          </option>
        </select>
      </div>
      <div class="control-group">
        <label for="teacher-select">选择教师:</label>
        <select id="teacher-select" v-model="selectedTeacherId" @change="clearTimetableAndWeek">
          <option value="" disabled>请选择教师</option>
          <option v-for="teacher in teachers" :key="teacher.id" :value="teacher.id">
            {{ teacher.name }}
          </option>
        </select>
      </div>
      <!-- New Week Selector -->
      <div class="control-group" v-if="selectedSemesterData && selectedSemesterData.total_weeks > 0">
        <label for="week-select-teacher">选择周次:</label>
        <select id="week-select-teacher" v-model="selectedWeek" @change="filterTimetableForWeek">
          <option value="0">所有周</option> <!-- Option to show all weeks -->
          <option v-for="week in availableWeeks" :key="week" :value="week">
            第 {{ week }} 周
          </option>
        </select>
      </div>
      <!-- End New Week Selector -->
      <button @click="fetchTeacherTimetable"
              :disabled="!selectedSemesterId || !selectedTeacherId || isLoading"
              class="button primary-button">
        <i class="icon-search"></i> {{ isLoading ? '查询中...' : '查询课表' }}
      </button>
      <button @click="exportTeacherTimetable"
              :disabled="!selectedSemesterId || !selectedTeacherId || allFetchedEntries.length === 0 || isLoadingExport"
              class="button success-button">
        <i class="icon-download"></i> {{ isLoadingExport ? '导出中...' : '导出Excel' }}
      </button>
    </div>

    <div v-if="isLoading" class="status-message info">正在加载课表...</div>
    <div v-if="errorMessage" class="status-message error">{{ errorMessage }}</div>

    <div v-if="!isLoading && displayedEntries.length > 0" class="timetable-display-area">
        <TimetableGridDisplay
            :entries="displayedEntries"
            :totalWeeks="selectedSemesterData ? selectedSemesterData.total_weeks : 0"
            :currentWeek="selectedWeek"
            viewType="teacher"
        />
    </div>
    <div v-if="!isLoading && hasSearched && displayedEntries.length === 0 && !errorMessage" class="status-message info">
      未查询到该教师在此学期{{ selectedWeek > 0 ? `第 ${selectedWeek} 周` : '' }}的排课数据。
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import axios from 'axios';
import TimetableGridDisplay from './TimetableGridDisplay.vue';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

const semesters = ref([]);
const teachers = ref([]);
const selectedSemesterId = ref('');
const selectedTeacherId = ref('');
const selectedWeek = ref(1); // Default to week 1, or 0 for "All Weeks"
const allFetchedEntries = ref([]); // To store all entries for the semester
const displayedEntries = ref([]); // Entries to be displayed (filtered by week)

const isLoading = ref(false);
const isLoadingExport = ref(false);
const errorMessage = ref('');
const hasSearched = ref(false);

const selectedSemesterData = computed(() => {
    return semesters.value.find(s => s.id === selectedSemesterId.value);
});

const availableWeeks = computed(() => {
  if (selectedSemesterData.value && selectedSemesterData.value.total_weeks > 0) {
    return Array.from({ length: selectedSemesterData.value.total_weeks }, (_, i) => i + 1);
  }
  return [];
});

onMounted(async () => {
  await fetchSemesters();
  await fetchTeachers();
  if (semesters.value.length > 0) {
    // Optionally select the first semester and week
    // selectedSemesterId.value = semesters.value[0].id;
    // selectedWeek.value = 1; // Or 0 if "All Weeks" is default
  }
});

const fetchSemesters = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    // Ensure total_weeks is a number. Backend should provide this.
    // If not, you might need to calculate it or have a default.
    semesters.value = response.data.map(s => ({
        ...s,
        total_weeks: parseInt(s.total_weeks, 10) || 18 // Fallback if not provided or invalid
    }));
  } catch (error) {
    errorMessage.value = '获取学期列表失败。';
    console.error(error);
  }
};

const fetchTeachers = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/teachers-list`);
    teachers.value = response.data;
  } catch (error) {
    errorMessage.value = '获取教师列表失败。';
    console.error(error);
  }
};

const clearTimetableAndWeek = () => {
    allFetchedEntries.value = [];
    displayedEntries.value = [];
    errorMessage.value = '';
    hasSearched.value = false;
    // selectedWeek.value = 1; // Reset week when teacher changes, or to 0 for "All Weeks"
};

const onSemesterChange = () => {
    clearTimetableAndWeek();
    selectedWeek.value = 1; // Reset to week 1 or 0 when semester changes
    // If you automatically fetch on semester change, call fetchTeacherTimetable here
};


const filterTimetableForWeek = () => {
    if (parseInt(selectedWeek.value, 10) === 0) { // "All Weeks" selected
        displayedEntries.value = [...allFetchedEntries.value];
    } else if (allFetchedEntries.value.length > 0) {
        const week = parseInt(selectedWeek.value, 10);
        displayedEntries.value = allFetchedEntries.value.filter(entry => entry.week_number === week);
    } else {
        displayedEntries.value = [];
    }
};

watch(selectedWeek, () => {
    // This function is now called directly by @change on week selector
    // but can also be useful if selectedWeek is changed programmatically
    filterTimetableForWeek();
});

watch(allFetchedEntries, () => {
    // When allFetchedEntries changes (new data loaded), re-filter based on current selectedWeek
    filterTimetableForWeek();
});


const fetchTeacherTimetable = async () => {
  if (!selectedSemesterId.value || !selectedTeacherId.value) return;
  isLoading.value = true;
  errorMessage.value = '';
  allFetchedEntries.value = []; // Clear previous full list
  // displayedEntries.value = []; // Will be cleared by allFetchedEntries watcher or filterTimetableForWeek
  hasSearched.value = true;
  try {
    const response = await axios.get(`${API_BASE_URL}/api/timetables/teacher/${selectedTeacherId.value}/semester/${selectedSemesterId.value}`);
    allFetchedEntries.value = response.data; // Store all entries
    // filterTimetableForWeek(); // Filter for the initially selected week (or all if selectedWeek is 0)
    // The watch on allFetchedEntries will trigger filterTimetableForWeek
  } catch (error) {
    errorMessage.value = `获取教师课表失败: ${error.response?.data?.message || error.message}`;
    console.error(error);
    allFetchedEntries.value = []; // Ensure it's empty on error
    // displayedEntries.value = [];
  } finally {
    isLoading.value = false;
  }
};

const exportTeacherTimetable = async () => {
  if (!selectedSemesterId.value || !selectedTeacherId.value) return;
  isLoadingExport.value = true;
  errorMessage.value = '';
  try {
    // The export endpoint already provides all data for the semester, which is usually desired for export
    const response = await axios.get(
      `${API_BASE_URL}/api/timetables/export/teacher/${selectedTeacherId.value}/semester/${selectedSemesterId.value}`,
      { responseType: 'blob' }
    );
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    const teacherName = teachers.value.find(t => t.id === parseInt(selectedTeacherId.value))?.name || 'UnknownTeacher';
    const semesterName = semesters.value.find(s => s.id === parseInt(selectedSemesterId.value))?.name || 'UnknownSemester';
    link.setAttribute('download', `教师课表_${teacherName}_${semesterName}.xlsx`);
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
/* Styles remain the same, ensure .control-group can accommodate the new select if needed */
.timetable-view { padding: 20px; max-width: 1200px; margin: auto; }
h2 { text-align: center; margin-bottom: 20px; }
.controls { display: flex; gap: 15px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; padding: 15px; background-color: #f8f9fa; border-radius: 8px;}
.control-group { display: flex; flex-direction: column; }
.control-group label { margin-bottom: 5px; font-weight: bold; font-size: 0.9em; }
.control-group select, .button { padding: 8px 12px; border-radius: 4px; border: 1px solid #ced4da; min-width: 150px; /* Ensure selects have some width */ }
.button { cursor: pointer; border: none; color: white; display: inline-flex; align-items: center; min-width: auto; /* Buttons don't need fixed min-width like selects */ }
.button i { margin-right: 6px; }
.primary-button { background-color: #007bff; }
.primary-button:hover:not(:disabled) { background-color: #0056b3; }
.success-button { background-color: #28a745; }
.success-button:hover:not(:disabled) { background-color: #1e7e34; }
.button:disabled { background-color: #cccccc; cursor: not-allowed; }
.status-message { padding: 10px; margin-top: 15px; border-radius: 4px; }
.info { background-color: #e6f7ff; border: 1px solid #91d5ff; color: #005280; }
.error { background-color: #fff1f0; border: 1px solid #ffa39e; color: #a8071a; }
.timetable-display-area { margin-top: 20px; }
.icon-search::before { content: '🔍';}
.icon-download::before { content: '📄';}
</style>
