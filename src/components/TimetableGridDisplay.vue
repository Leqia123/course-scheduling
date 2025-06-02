<template>
  <div class="timetable-grid-container">
    <div v-if="processedTimetable.length === 0" class="no-data">
      没有课表数据可以显示。
    </div>
    <div v-else>
      <div class="week-navigation" v-if="totalWeeks > 1">
        <button @click="prevWeek" :disabled="currentWeek === 1">&lt; 上一周</button>
        <span>第 {{ currentWeek }} 周 / 共 {{ totalWeeks }} 周</span>
        <button @click="nextWeek" :disabled="currentWeek === totalWeeks">下一周 &gt;</button>
      </div>
      <div class="table-responsive">
        <table class="timetable-grid">
          <thead>
            <tr>
              <th>时间</th>
              <th v-for="day in daysOrder" :key="day">{{ day }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="period in periodsOrder" :key="period">
              <td>{{ formatPeriod(period) }}</td>
              <td v-for="day in daysOrder" :key="day">
                <div v-if="processedTimetable[currentWeek -1] && processedTimetable[currentWeek-1][day] && processedTimetable[currentWeek-1][day][period]"
                     class="timetable-cell-content">
                  <div><strong>{{ processedTimetable[currentWeek-1][day][period].course_name }}</strong></div>
                  <div v-if="viewType === 'major'">{{ processedTimetable[currentWeek-1][day][period].teacher_name }}</div>
                  <div v-if="viewType === 'teacher'">({{ processedTimetable[currentWeek-1][day][period].major_name }})</div>
                  <div>@ {{ processedTimetable[currentWeek-1][day][period].classroom_name }}</div>
                  <div class="course-type">({{ processedTimetable[currentWeek-1][day][period].course_type }})</div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  entries: {
    type: Array,
    required: true,
  },
  totalWeeks: {
    type: Number,
    required: true,
    default: 1
  },
  viewType: { // 'major' or 'teacher'
    type: String,
    default: 'major'
  }
});

const currentWeek = ref(1);
// Define the order of days and periods for display
const daysOrder = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
// Determine periods dynamically or use a fixed set if known
// For simplicity, let's assume up to 4 or 5 periods are common
const periodsOrder = ref([1, 2, 3, 4, 5]); // Default, can be made dynamic

watch(() => props.totalWeeks, (newVal) => {
    if (newVal > 0 && currentWeek.value > newVal) {
        currentWeek.value = newVal;
    } else if (newVal === 0 && currentWeek.value !== 1) {
        currentWeek.value = 1; // Reset if totalWeeks becomes 0
    } else if (newVal > 0 && currentWeek.value === 0){ // if currentWeek was 0
        currentWeek.value = 1;
    }
}, { immediate: true });


const processedTimetable = computed(() => {
  if (!props.entries || props.entries.length === 0 || props.totalWeeks === 0) {
      return [];
  }

  // Initialize a 3D array: weeks[days[periods]]
  const timetable = Array(props.totalWeeks).fill(null).map(() =>
    daysOrder.reduce((acc, day) => {
      acc[day] = periodsOrder.value.reduce((pAcc, period) => {
        pAcc[period] = null;
        return pAcc;
      }, {});
      return acc;
    }, {})
  );

  let maxPeriod = 0;
  props.entries.forEach(entry => {
    if (entry.week_number > 0 && entry.week_number <= props.totalWeeks) {
      const weekIndex = entry.week_number - 1;
      if (daysOrder.includes(entry.day_of_week) && entry.period) {
        timetable[weekIndex][entry.day_of_week][entry.period] = {
          course_name: entry.course_name,
          teacher_name: entry.teacher_name,
          major_name: entry.major_name, // Add if available in entry
          classroom_name: entry.classroom_name,
          course_type: entry.course_type
          // Add more details if needed
        };
        if (entry.period > maxPeriod) maxPeriod = entry.period;
      }
    }
  });
    // Dynamically set periodsOrder based on maxPeriod found, if needed
    if (maxPeriod > 0 && maxPeriod > periodsOrder.value.length) {
       periodsOrder.value = Array.from({length: maxPeriod}, (_, i) => i + 1);
       // Re-initialize timetable structure if periodsOrder changed, though this computed will re-run
    }


  return timetable;
});

const formatPeriod = (period) => {
  // Example: 1 -> 1-2节, 2 -> 3-4节 etc. Adjust as per your timeslot definition
  // This is a placeholder. You need to map 'period' (e.g., 1, 2, 3, 4) to actual time strings.
  // Or, if your `entry.period` IS the display string like "1-2节", just return it.
  // Assuming period is 1, 2, 3, 4, 5 for 1-2, 3-4, 5-6, 7-8, 9-10
  // This needs to match how your `time_slots` `period` field is defined.
  // Let's assume your `entry.period` from backend is 1, 2, 3, 4 representing blocks.
  // For a more specific display, you might need start_time, end_time from the entry.
  const periodMap = {
      1: "1-2节",
      2: "3-4节",
      3: "午间/5节", // Example
      4: "6-7节",
      5: "8-9节",
      // Add more if needed
  };
  // If your period numbers in DB are already 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 (for single sessions)
  // then this mapping is different.
  // For now, using the key as is.
  return periodMap[period] || `第${period}大节`;
};

const prevWeek = () => {
  if (currentWeek.value > 1) {
    currentWeek.value--;
  }
};

const nextWeek = () => {
  if (currentWeek.value < props.totalWeeks) {
    currentWeek.value++;
  }
};

</script>

<style scoped>
.timetable-grid-container {
  font-family: Arial, sans-serif;
}
.no-data {
  text-align: center;
  padding: 20px;
  color: #666;
}
.week-navigation {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding: 10px;
  background-color: #f0f0f0;
  border-radius: 4px;
}
.week-navigation button {
  padding: 5px 10px;
  cursor: pointer;
  border: 1px solid #ccc;
  background-color: #fff;
  border-radius: 3px;
}
.week-navigation button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.table-responsive {
    overflow-x: auto;
}
.timetable-grid {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed; /* Important for equal column widths if desired */
}
.timetable-grid th, .timetable-grid td {
  border: 1px solid #ccc;
  padding: 8px;
  text-align: center;
  min-width: 100px; /* Minimum width for content */
  height: 80px; /* Fixed height for cells */
  vertical-align: top;
}
.timetable-grid th {
  background-color: #e9ecef;
  font-weight: bold;
}
.timetable-grid td {
    background-color: #fff;
}
.timetable-cell-content {
  font-size: 0.85em;
  line-height: 1.3;
}
.timetable-cell-content div {
    margin-bottom: 3px;
}
.course-type {
    font-style: italic;
    color: #555;
    font-size: 0.9em;
}
</style>
