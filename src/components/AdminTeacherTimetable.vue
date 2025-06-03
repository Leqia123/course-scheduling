<template>
  <div class="timetable-view">
    <h2>查询教师课表</h2>

    <div class="controls">
      <!-- 学期选择 -->
      <div class="control-group">
        <label for="semester-select-teacher">选择学期:</label>
        <select id="semester-select-teacher" v-model="selectedSemesterId" @change="onSemesterChange">
          <option value="" disabled>请选择学期</option>
          <option v-for="semester in semesters" :key="semester.id" :value="semester.id">
            {{ semester.name }} {{ semester.total_weeks ? `(共${semester.total_weeks}周)` : '' }}
          </option>
        </select>
      </div>

      <!-- 教师选择 -->
      <div class="control-group">
        <label for="teacher-select">选择教师:</label>
        <select id="teacher-select" v-model="selectedTeacherId" @change="clearTimetableAndWeek" :disabled="!selectedSemesterId">
          <option value="" disabled>请选择教师</option>
          <option v-for="teacher in teachers" :key="teacher.id" :value="teacher.id">
            {{ teacher.name }}
          </option>
        </select>
      </div>

      <!-- 周数选择 -->
      <!-- 移除了 v-if 条件，使周数选择始终显示 -->
      <!-- Select本身通过:disabled控制是否可用 -->
      <div class="control-group">
        <label for="week-select-teacher">选择周次:</label>
        <!-- selectedWeek 绑定当前选中的周数 -->
        <!-- 通过 :disabled 属性控制周数选择器是否可用 -->
        <select id="week-select-teacher" v-model="selectedWeek" :disabled="!selectedSemesterId || availableWeeks.length === 0">
          <!-- 移除 "所有周" 选项，因为 TimetableGridDisplay 当前设计为显示单周 -->
          <!-- <option value="0">所有周</option> -->
          <!-- Week numbers are generated from 1 to total_weeks -->
          <option value="" disabled v-if="availableWeeks.length === 0">请选择周次</option> <!-- 当没有可用周次时显示此提示 -->
          <option v-for="week in availableWeeks" :key="week" :value="week">
            第 {{ week }} 周
          </option>
        </select>
      </div>

      <!-- 查询按钮 -->
      <!-- 注意：这里的查询按钮现在是获取【整个学期】的数据 -->
      <!-- 将查询按钮包裹在 control-group action-group div 中 -->
      <div class="control-group action-group">
        <button @click="fetchTeacherTimetable"
                :disabled="!selectedSemesterId || !selectedTeacherId || isLoading"
                class="button primary-button">
          <i class="icon-search"></i> {{ isLoading ? '查询中...' : '查询课表' }}
        </button>
      </div>

      <!-- 导出按钮 -->
      <!-- 导出的是该教师该学期的全部课表 -->
      <!-- 将导出按钮包裹在 control-group action-group div 中 -->
      <div class="control-group action-group">
        <button @click="exportTeacherTimetable"
                :disabled="!selectedSemesterId || !selectedTeacherId || allFetchedEntries.length === 0 || isLoadingExport"
                class="button success-button">
          <i class="icon-download"></i> {{ isLoadingExport ? '导出中...' : '导出学期Excel' }}
        </button>
      </div>
    </div>

    <div v-if="isLoading" class="status-message info">正在加载课表...</div>
    <div v-if="errorMessage" class="status-message error">{{ errorMessage }}</div>

    <!-- 显示当前选定周的课表 -->
    <!-- 仅当有 allFetchedEntries 且 filterTimetableForWeek 过滤后有结果时显示 -->
    <div v-if="!isLoading && displayedEntries.length > 0" class="timetable-display-area">
        <!--
            调用 TimetableGridDisplay:
            - entries: 传递过滤后的单周数据
            - totalWeeks: 传递 1 (表示显示单周)
            - actualWeekNumber: 传递当前选中的周数，用于在 grid header 显示
            - viewType: teacher
        -->
        <TimetableGridDisplay
            :entries="displayedEntries"
            :totalWeeks="1"
            :actualWeekNumber="selectedWeek"
            viewType="teacher"
        />
    </div>

    <!-- 当获取到数据但当前周过滤后为空时的提示 -->
     <div v-if="!isLoading && hasSearched && allFetchedEntries.length > 0 && displayedEntries.length === 0 && !errorMessage" class="status-message info">
      该教师在此学期、**第 {{ selectedWeek }} 周**没有排课数据。请尝试选择其他周次。
    </div>
    <!-- 当没有任何数据被获取时的提示 -->
     <div v-if="!isLoading && hasSearched && allFetchedEntries.length === 0 && !errorMessage" class="status-message info">
      未查询到该教师在此学期的任何排课数据。
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
// selectedWeek 用于过滤并传递给 TimetableGridDisplay
// 默认值为 1，或在 onSemesterChange 中设置
const selectedWeek = ref(1);
// allFetchedEntries 存储从后端获取的该教师该学期所有周的全部数据
const allFetchedEntries = ref([]);
// displayedEntries 是根据 selectedWeek 从 allFetchedEntries 过滤出的单周数据
const displayedEntries = ref([]);

const isLoading = ref(false);
const isLoadingExport = ref(false);
const errorMessage = ref('');
const hasSearched = ref(false); // 标记是否执行过查询

// 计算属性：获取选中的学期对象，包含 total_weeks
const selectedSemesterData = computed(() => {
    // 确保 selectedSemesterId.value 是 number 类型，如果它是 string，需要转换
    const idToFind = selectedSemesterId.value; // 默认 v-model 应该是 Number 如果 input 是 type="number" 或 select options value 是数字
    return semesters.value.find(s => s.id === idToFind);
});

// 计算属性：根据选中的学期计算可用周数列表 (1 到 total_weeks)
const availableWeeks = computed(() => {
  const total = selectedSemesterData.value?.total_weeks;
  if (total && total > 0) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  return []; // 如果没有有效周数，返回空数组
});

// 组件挂载时获取基础数据
onMounted(async () => {
  await fetchSemesters();
  await fetchTeachers();
  // 可以在这里尝试默认选中第一个学期
  // if (semesters.value.length > 0) {
  //     selectedSemesterId.value = semesters.value[0].id;
  //     // 此时 totalWeeks computed 会更新，availableWeeks 也会更新
  //     // selectedWeek 应该默认设置为 1
  // }
});

// 获取学期列表 (包含 total_weeks)
const fetchSemesters = async () => {
  isLoading.value = true; // 开始加载时设置状态
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    // 确保 total_weeks 是数字，并且 id 也是数字以便 v-model 匹配
    semesters.value = response.data.map(s => ({
        ...s,
        id: Number(s.id), // 确保ID是数字
        total_weeks: Number(s.total_weeks) || 18 // Fallback
    }));
  } catch (error) {
    errorMessage.value = '获取学期列表失败。';
    console.error(error);
  } finally {
      isLoading.value = false; // 结束加载时取消状态
  }
};

// 获取教师列表
const fetchTeachers = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/teachers-list`);
     // 确保 id 是数字以便 v-model 匹配
    teachers.value = response.data.map(t => ({
        ...t,
        id: Number(t.id) // 确保ID是数字
    }));
  } catch (error) {
    errorMessage.value = '获取教师列表失败。';
    console.error(error);
  }
};

// 清空课表数据和状态信息，并重置周数选择
const clearTimetableAndWeek = () => {
    allFetchedEntries.value = [];
    displayedEntries.value = [];
    errorMessage.value = '';
    hasSearched.value = false;
    selectedWeek.value = 1; // 重置周数选择为 1
};

// 处理学期选择变化
const onSemesterChange = () => {
    // 清空相关数据和状态
    clearTimetableAndWeek();
    // 同时清空选中的教师，强制用户重新选择教师以获取新学期的课表
    selectedTeacherId.value = '';
    // selectedWeek 在 clearTimetableAndWeek 中已重置为 1
    // 当学期变化时，availableWeeks 会更新，如果新的学期有周数，selectedWeek=1 是一个有效值
    // 如果新的学期没有周数，availableWeeks 为空，select 会被禁用
};

// watch selectedWeek 的变化，触发过滤 displayedEntries
// 注：@change="filterTimetableForWeek" 在 <select> 上也可以工作
// 但 watch 更 Vue 风格，当 selectedWeek 被代码改变时也能响应
watch(selectedWeek, (newWeek) => {
    console.log('Selected week changed to:', newWeek);
    // 只有在 selectedWeek 有值（不是初始的空字符串或者其他无效值）且 allFetchedEntries 有数据时才过滤
    if (newWeek !== null && newWeek !== undefined && allFetchedEntries.value.length > 0) {
      filterTimetableForWeek();
    } else {
      // 如果选择周次被清空，或者还没获取到全部数据，清空显示的数据
       displayedEntries.value = [];
    }

});

// watch allFetchedEntries 的变化，也触发过滤 displayedEntries
// 首次获取数据后，allFetchedEntries 会更新，从而触发这个 watch
watch(allFetchedEntries, (newEntries) => {
     console.log('allFetchedEntries updated. Total entries:', newEntries.length);
     // 当所有数据更新后，根据当前的 selectedWeek 过滤显示
     // 确保 selectedWeek 有一个有效值，这里默认是 1
     if (selectedWeek.value !== null && selectedWeek.value !== undefined && newEntries.length > 0) {
        filterTimetableForWeek();
     } else {
        displayedEntries.value = []; // 如果没有 fetched data 或 selectedWeek 无效，清空显示
     }
}, { deep: true }); // deep watch is needed if entries might change internally (though not expected here)


// 根据 selectedWeek 过滤要显示的数据
const filterTimetableForWeek = () => {
    console.log(`Filtering timetable for week: ${selectedWeek.value}`);
    if (!allFetchedEntries.value || allFetchedEntries.value.length === 0) {
        displayedEntries.value = [];
        console.log('No allFetchedEntries to filter.');
        return;
    }

    // 确保 selectedWeek.value 是一个有效的周数 (在 availableWeeks 范围内)
    // 如果 selectedWeek.value 不是数字或者超出范围，则过滤结果为空
    const weekToDisplay = Number(selectedWeek.value); // 确保是数字
    if (isNaN(weekToDisplay) || !availableWeeks.value.includes(weekToDisplay)) {
        displayedEntries.value = [];
        console.warn(`Selected week ${selectedWeek.value} is invalid or outside available range.`);
        return;
    }


    // TimetableGridDisplay 只需要单周数据
    displayedEntries.value = allFetchedEntries.value.filter(entry => entry.week_number === weekToDisplay);

    console.log(`Filtered entries for week ${weekToDisplay}: ${displayedEntries.value.length}`);

    // 如果过滤后没有数据，可以考虑重置 selectedWeek 到 1，或者保持原样让用户看到空白
    // 这里选择保持原样，并显示 "未查询到该周排课" 的提示
     if (displayedEntries.value.length === 0 && hasSearched.value) {
         console.warn(`No entries found for week ${weekToDisplay} after filtering.`);
     }
};


// 获取指定教师、学期的所有课表数据
const fetchTeacherTimetable = async () => {
  // 检查是否已选择学期和教师
  if (!selectedSemesterId.value || !selectedTeacherId.value) {
      errorMessage.value = '请先选择学期和教师。';
      return;
  }

  isLoading.value = true;
  errorMessage.value = '';
  allFetchedEntries.value = []; // 清空旧的全部数据列表
  // displayedEntries 会因为 allFetchedEntries 的 watch 自动更新
  hasSearched.value = true; // 标记已执行查询

  try {
    // 调用获取该教师该学期所有周数据的 API
    const response = await axios.get(
      `${API_BASE_URL}/api/timetables/teacher/${selectedTeacherId.value}/semester/${selectedSemesterId.value}`
      // 这里不需要 week 参数，后端应该返回所有周
    );

    // 确保返回的是数组
    allFetchedEntries.value = Array.isArray(response.data) ? response.data : [];

    console.log(`Fetched ${allFetchedEntries.value.length} total entries for the semester.`);

    // fetch 成功后，watch(allFetchedEntries) 会被触发，进而调用 filterTimetableForWeek
    // filterTimetableForWeek 会根据当前的 selectedWeek 过滤并更新 displayedEntries

    // 如果获取到数据，并且 selectedWeek 当前不是 1 (例如默认是1，但用户改了)，
    // 则 filterTimetableForWeek 会根据 selectedWeek 过滤
    // 如果 selectedWeek 恰好是 1，也会过滤出第 1 周的数据

     if (allFetchedEntries.value.length > 0) {
         // 假设获取到数据后默认显示第一周的数据，并确保 selectedWeek 是 1
         // 如果用户已经在获取前选择了其他周，保持该周不变
         // 如果 availableWeeks 数组有值，确保 selectedWeek 在有效范围内，否则设置为 1
         if (!availableWeeks.value.includes(Number(selectedWeek.value))) {
              selectedWeek.value = availableWeeks.value.length > 0 ? availableWeeks.value[0] : 1;
         }
         // watch(allFetchedEntries) 会触发过滤
     } else {
         // 如果没有获取到任何数据， displayedEntries 会被过滤成空
          displayedEntries.value = [];
     }


  } catch (error) {
    errorMessage.value = `获取教师课表失败: ${error.response?.data?.message || error.message}`;
    console.error(error);
    allFetchedEntries.value = []; // 出错时清空
    displayedEntries.value = []; // 出错时清空
  } finally {
    isLoading.value = false;
  }
};

// 导出教师课表 (该教师该学期全部数据)
const exportTeacherTimetable = async () => {
  // 导出时使用 allFetchedEntries.length > 0 来判断是否有数据可导出
  if (!selectedSemesterId.value || !selectedTeacherId.value || allFetchedEntries.value.length === 0) return;
  isLoadingExport.value = true;
  errorMessage.value = '';
  try {
    // 调用导出该教师该学期全部课表的 API
    const response = await axios.get(
      `${API_BASE_URL}/api/timetables/export/teacher/${selectedTeacherId.value}/semester/${selectedSemesterId.value}`,
      { responseType: 'blob' }
    );
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    const teacherName = teachers.value.find(t => t.id === Number(selectedTeacherId.value))?.name || 'UnknownTeacher';
    const semesterName = semesters.value.find(s => s.id === Number(selectedSemesterId.value))?.name || 'UnknownSemester';
    link.setAttribute('download', `教师课表_${teacherName}_${semesterName}_(全学期).xlsx`);
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
/* AdminTeacherTimetable.vue 样式 */
/* 复制并调整 AdminStudentTimetable.vue 的样式 */
.timetable-view { padding: 20px; max-width: 1200px; margin: auto; }
h2 { text-align: center; margin-bottom: 20px; }
.controls {
    display: flex;
    gap: 15px;
    margin-bottom: 20px;
    align-items: flex-end; /* 让按钮和下拉框底部对齐 */
    flex-wrap: wrap; /* 允许换行 */
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
}
.control-group {
    display: flex;
    flex-direction: column;
    /* Add flex properties similar to AdminStudentTimetable.vue */
    flex: 1 1 200px; /* Adjust minimum width as needed */
    margin-bottom: 10px; /* Vertical spacing for wrapping */
}
.control-group label { margin-bottom: 5px; font-weight: bold; font-size: 0.9em; }
.control-group select {
    padding: 8px 12px;
    border-radius: 4px;
    border: 1px solid #ced4da;
    width: 100%; /* Make dropdown fill its container */
    height: 38px; /* Match button height */
    box-sizing: border-box;
}
.action-group {
    display: flex;
    align-items: flex-end; /* Ensure buttons align at the bottom */
    /* Add flex properties for button group */
    flex: 1 1 150px; /* Adjust minimum width as needed */
}
.button {
    padding: 8px 15px; /* Adjust button padding */
    height: 38px; /* Keep consistent with dropdowns */
    cursor: pointer;
    border: none;
    color: white;
    display: inline-flex;
    align-items: center;
    border-radius: 4px;
    box-sizing: border-box;
    white-space: nowrap; /* Prevent button text wrapping */
    /* Add margin-right to separate buttons within the action-group if needed, or rely on parent gap */
}
.button + .button { /* Add space between buttons if they are siblings within action-group */
  margin-left: 10px;
}
.primary-button { background-color: #007bff; }
.primary-button:hover:not(:disabled) { background-color: #0056b3; }
.success-button { background-color: #28a745; }
.success-button:hover:not(:disabled) { background-color: #1e7e34; }
.button:disabled { background-color: #cccccc; cursor: not-allowed; }
.status-message { padding: 10px; margin-top: 15px; border-radius: 4pt; }
.info { background-color: #e6f7ff; border: 1px solid #91d5ff; color: #005280; }
.error { background-color: #fff1f0; border: 1px solid #ffa39e; color: #a8071a; }
.timetable-display-area { margin-top: 20px; }
.icon-search::before { content: '🔍';}
.icon-download::before { content: '📄';}
</style>
