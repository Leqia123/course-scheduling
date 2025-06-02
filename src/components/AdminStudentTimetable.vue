<template>
  <div class="timetable-view">
    <h2>查询专业/学生课表</h2>

    <div class="controls">
      <div class="control-group">
        <label for="semester-select-major">选择学期:</label>
        <select id="semester-select-major" v-model="selectedSemesterId" @change="clearTimetable">
          <option value="" disabled>请选择学期</option>
          <option v-for="semester in semesters" :key="semester.id" :value="semester.id">
            {{ semester.name }}
          </option>
        </select>
      </div>
      <div class="control-group">
        <label for="major-select">选择专业:</label>
        <select id="major-select" v-model="selectedMajorId" @change="clearTimetable">
          <option value="" disabled>请选择专业</option>
          <option v-for="major in majors" :key="major.id" :value="major.id">
            {{ major.name }}
          </option>
        </select>
      </div>
      <button @click="fetchMajorTimetable"
              :disabled="!selectedSemesterId || !selectedMajorId || isLoading"
              class="button primary-button">
        <i class="icon-search"></i> {{ isLoading ? '查询中...' : '查询课表' }}
      </button>
      <button @click="exportMajorTimetable"
              :disabled="!selectedSemesterId || !selectedMajorId || timetableEntries.length === 0 || isLoadingExport"
              class="button success-button">
        <i class="icon-download"></i> {{ isLoadingExport ? '导出中...' : '导出Excel' }}
      </button>
    </div>

    <div v-if="isLoading" class="status-message info">正在加载课表...</div>
    <div v-if="errorMessage" class="status-message error">{{ errorMessage }}</div>

    <div v-if="!isLoading && timetableEntries.length > 0" class="timetable-display-area">
         <TimetableGridDisplay
            :entries="timetableEntries"
            :totalWeeks="selectedSemesterData ? selectedSemesterData.total_weeks : 0"
            viewType="major"
        />
    </div>
     <div v-if="!isLoading && hasSearched && timetableEntries.length === 0 && !errorMessage" class="status-message info">
      未查询到该专业在此学期的排课数据。
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import axios from 'axios';
import TimetableGridDisplay from './TimetableGridDisplay.vue'; // Re-use the display component

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

const semesters = ref([]);
const majors = ref([]); // Changed from teachers
const selectedSemesterId = ref('');
const selectedMajorId = ref(''); // Changed
const timetableEntries = ref([]);
const isLoading = ref(false);
const isLoadingExport = ref(false);
const errorMessage = ref('');
const hasSearched = ref(false);

const selectedSemesterData = computed(() => {
    return semesters.value.find(s => s.id === selectedSemesterId.value);
});

onMounted(async () => {
  await fetchSemesters();
  await fetchMajors(); // Changed
});

const fetchSemesters = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    semesters.value = response.data;
  } catch (error) {
    errorMessage.value = '获取学期列表失败。';
    console.error(error);
  }
};

const fetchMajors = async () => { // Changed
  try {
    // Assuming you have an endpoint like /api/majors-list from previous work
    const response = await axios.get(`${API_BASE_URL}/api/majors-list`);
    majors.value = response.data;
  } catch (error) {
    errorMessage.value = '获取专业列表失败。';
    console.error(error);
  }
};

const clearTimetable = () => {
    timetableEntries.value = [];
    errorMessage.value = '';
    hasSearched.value = false;
};

const fetchMajorTimetable = async () => { // Changed
  if (!selectedSemesterId.value || !selectedMajorId.value) return;
  isLoading.value = true;
  errorMessage.value = '';
  timetableEntries.value = [];
  hasSearched.value = true;
  try {
    const response = await axios.get(`${API_BASE_URL}/api/timetables/major/${selectedMajorId.value}/semester/${selectedSemesterId.value}`);
    timetableEntries.value = response.data;
  } catch (error) {
    errorMessage.value = `获取专业课表失败: ${error.response?.data?.message || error.message}`;
    console.error(error);
  } finally {
    isLoading.value = false;
  }
};

const exportMajorTimetable = async () => { // Changed
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
    const majorName = majors.value.find(m => m.id === selectedMajorId.value)?.name || 'UnknownMajor';
    const semesterName = semesters.value.find(s => s.id === selectedSemesterId.value)?.name || 'UnknownSemester';
    link.setAttribute('download', `专业课表_${majorName}_${semesterName}.xlsx`);
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
/* Styles are identical to AdminTeacherTimetable.vue, or can be shared */
.timetable-view { padding: 20px; max-width: 1200px; margin: auto; }
h2 { text-align: center; margin-bottom: 20px; }
.controls { display: flex; gap: 15px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; padding: 15px; background-color: #f8f9fa; border-radius: 8px;}
.control-group { display: flex; flex-direction: column; }
.control-group label { margin-bottom: 5px; font-weight: bold; font-size: 0.9em; }
.control-group select, .button { padding: 8px 12px; border-radius: 4px; border: 1px solid #ced4da; }
.button { cursor: pointer; border: none; color: white; display: inline-flex; align-items: center; }
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
