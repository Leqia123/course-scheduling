<template>
  <div class="timetable-grid-container">
    <!-- Optional: Display current week number if showing only one week -->
    <!-- Ensure actualWeekNumber is passed from the parent component -->
    <h3 v-if="totalWeeks === 1 && actualWeekNumber">第 {{ actualWeekNumber }} 周课表</h3>

    <div class="timetable-grid-scrollable">
      <table class="timetable-grid">
        <thead>
          <tr>
            <th>时间/星期</th>
            <th v-for="day in daysOrder" :key="day">{{ day }}</th>
          </tr>
        </thead>
        <tbody>
          <!-- Iterate through time periods -->
          <tr v-for="(periodTimes, period) in processedPeriods" :key="period">
            <td>
              <div class="period-info">
                <div class="period-number">{{ period }}</div>
                <div class="period-time">{{ periodTimes.start }} - {{ periodTimes.end }}</div>
              </div>
            </td>
            <!-- Iterate through days of the week -->
            <!-- We are only displaying one week at a time (actualWeekNumber) -->
            <td v-for="day in daysOrder" :key="day">
              <!-- Check if there are entries for the current week, day, and period -->
              <!-- processedTimetable is { weekNumber: { dayOfWeek: { period: [entries] } } } -->
              <div v-if="processedTimetable[actualWeekNumber - 1] && processedTimetable[actualWeekNumber-1][day] && processedTimetable[actualWeekNumber-1][day][period] && processedTimetable[actualWeekNumber-1][day][period].length > 0"
                   class="timetable-cell-content">
                <!-- Display each entry in the cell -->
                <div v-for="(item, itemIndex) in processedTimetable[actualWeekNumber-1][day][period]" :key="item.id || itemIndex">
                  <div><strong>{{ item.course_name }}</strong></div>
                  <!-- Conditionally display teacher/major based on viewType -->
                  <!-- Student view might show teacher name, but not major -->
                  <!-- Teacher view might show major name, but not teacher name -->
                  <!-- Major view shows both -->
                  <div v-if="viewType === 'major' && item.teacher_name">授课教师: {{ item.teacher_name }}</div>
                  <div v-if="viewType === 'major' && item.major_name">专业: {{ item.major_name }}</div>

                  <div v-if="viewType === 'teacher' && item.major_name">专业: {{ item.major_name }}</div>
                  <!-- Teachers' own view shouldn't repeat their name -->
                  <!-- <div v-if="viewType === 'teacher' && item.teacher_name">教师: {{ item.teacher_name }}</div> -->

                  <div v-if="viewType === 'student' && item.teacher_name">授课教师: {{ item.teacher_name }}</div>
                  <!-- Students' own view shouldn't repeat their major -->
                  <!-- <div v-if="viewType === 'student' && item.major_name">专业: {{ item.major_name }}</div> -->


                  <div v-if="item.classroom_name">地点: {{ item.classroom_name }}</div>
                   <div class="course-type" v-if="item.course_type">类型: {{ item.course_type }}</div>


                  <!-- Add a separator if there are multiple entries in the same cell -->
                  <hr v-if="processedTimetable[actualWeekNumber-1][day][period].length > 1 && itemIndex < processedTimetable[actualWeekNumber-1][day][period].length - 1">
                </div>
              </div>
              <!-- Empty cell if no entries -->
              <div v-else class="timetable-cell-empty"></div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watchEffect } from 'vue';

// Define props received from the parent component
const props = defineProps({
  entries: {
    type: Array,
    required: true
  },
  totalWeeks: { // The total number of weeks in the semester (needed for full semester view)
    type: Number,
    default: 1 // Default to 1 as student/teacher views usually show one week
  },
  actualWeekNumber: { // The specific week number being displayed (e.g., 5 for 5th week)
     type: Number,
     default: 1 // Default to week 1
  },
  viewType: { // 'major', 'teacher', 'student' - helps customize display
    type: String,
    default: 'major',
    validator: (value) => ['major', 'teacher', 'student', 'admin'].includes(value)
  }
});

// Define the order of days of the week (ensure this matches backend day_of_week values)
const daysOrder = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

// Define standard time periods and placeholder start/end times (these should ideally come from backend or config)
// Using placeholders for now, but backend time_slots could provide actual times
const allPeriods = Array.from({ length: 12 }, (_, i) => i + 1); // Assuming up to 12 periods
const placeholderTimes = [
  { start: '08:00', end: '09:30' }, { start: '09:40', end: '11:10' },
  { start: '13:30', end: '15:00' }, { start: '15:10', end: '16:40' },
  { start: '17:00', end: '18:30' }, { start: '18:40', end: '20:10' },
  { start: '20:20', end: '21:50' }, // Add more if needed based on time_slots
  // Placeholders for periods 8-12 if your system supports them
  { start: '??:??', end: '??:??' }, { start: '??:??', end: '??:??' },
  { start: '??:??', end: '??:??' }, { start: '??:??', end: '??:??' },
];

// Process time slots from entries to determine periods and times
const processedPeriods = computed(() => {
    // Build a map of period number to start/end time
    const periodMap = {};
    props.entries.forEach(entry => {
        if (entry.period && entry.start_time && entry.end_time) {
            // Use backend times if available
            periodMap[entry.period] = {
                start: entry.start_time.substring(0, 5), // Assuming HH:MM:SS format, take HH:MM
                end: entry.end_time.substring(0, 5)
            };
        }
    });

    // Sort periods numerically and ensure all standard periods up to max used are included
    const periodsInEntries = Object.keys(periodMap).map(Number).sort((a, b) => a - b);
     const maxPeriod = periodsInEntries.length > 0 ? Math.max(...periodsInEntries) : 0;

     const finalPeriods = {};
     for (let p = 1; p <= maxPeriod; p++) {
         finalPeriods[p] = periodMap[p] || placeholderTimes[p - 1] || { start: '??:??', end: '??:??' };
     }

     return finalPeriods;
});


// Process the raw entries into a nested structure for easy table rendering
// Structure: { weekNumber: { dayOfWeek: { period: [entry, entry, ...] } } }
const processedTimetable = ref({});

// Use watchEffect to re-process whenever entries, totalWeeks, or actualWeekNumber changes
watchEffect(() => {
  const tempTimetable = {};

  // Initialize structure for the relevant weeks
  // If totalWeeks > 1, initialize for all weeks. If totalWeeks is 1, only initialize for actualWeekNumber.
  const weeksToProcess = props.totalWeeks > 1 ? Array.from({ length: props.totalWeeks }, (_, i) => i + 1) : [props.actualWeekNumber];

  weeksToProcess.forEach(weekNum => {
      tempTimetable[weekNum - 1] = {}; // Use 0-based index for array structure
      daysOrder.forEach(day => {
          tempTimetable[weekNum - 1][day] = {};
          // No need to initialize periods here, add only if entries exist
      });
  });


  props.entries.forEach(entry => {
    // Ensure necessary fields exist and are in expected format
    if (entry.week_number && entry.day_of_week && entry.period) {
        const weekIndex = Number(entry.week_number) - 1; // Convert to 0-based index

        // Ensure the week, day, and period structure exists
        if (!tempTimetable[weekIndex]) {
           tempTimetable[weekIndex] = {};
        }
         if (!tempTimetable[weekIndex][entry.day_of_week]) {
             tempTimetable[weekIndex][entry.day_of_week] = {};
         }
        if (!tempTimetable[weekIndex][entry.day_of_week][entry.period]) {
          tempTimetable[weekIndex][entry.day_of_week][entry.period] = [];
        }

        // Add the entry to the corresponding cell
        tempTimetable[weekIndex][entry.day_of_week][entry.period].push(entry);
    } else {
        console.warn('TimetableGridDisplay: Skipping entry due to missing week, day, or period:', entry);
    }
  });

   // Optional: Sort entries within a cell if needed (e.g., by course name)
   weeksToProcess.forEach(weekNum => {
       const weekData = tempTimetable[weekNum - 1];
       if(weekData) {
           daysOrder.forEach(day => {
               const dayData = weekData[day];
               if(dayData) {
                   Object.keys(dayData).forEach(period => {
                       // Example sort: by course name
                       dayData[period].sort((a, b) => a.course_name.localeCompare(b.course_name));
                   });
               }
           });
       }
   });


  processedTimetable.value = tempTimetable;
  console.log('Processed Timetable Structure:', processedTimetable.value);
});

// Expose processedTimetable if parent needs to access it (optional)
// defineExpose({ processedTimetable });

</script>

<style scoped>
.timetable-grid-container {
  overflow-x: auto; /* Add horizontal scroll for the container */
}

.timetable-grid-scrollable {
    overflow-x: auto; /* Allow scrolling if the table is wider than the container */
    width: 100%; /* Take full width */
}

.timetable-grid {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
  min-width: 800px; /* Ensure minimum width to prevent excessive squeezing */
}

.timetable-grid th,
.timetable-grid td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: center;
  vertical-align: top; /* Align content to the top */
}

.timetable-grid th {
  background-color: #f2f2f2;
  font-weight: bold;
  white-space: nowrap; /* Prevent header text from wrapping */
}

.period-info {
    font-weight: bold;
    white-space: nowrap;

}
.period-time {
    font-size: 0.8em;
    font-weight: normal;
}

.timetable-cell-content {
    min-height: 60px; /* Ensure cells have a minimum height */
    text-align: center; /* Align content left within the cell */
}

.timetable-cell-content div {
    margin-bottom: 5px; /* Spacing between items in the same cell */
}
.timetable-cell-content div:last-child {
    margin-bottom: 0;
}

.timetable-cell-empty {
    min-height: 60px; /* Match min-height for empty cells */
}

.timetable-cell-content hr {
    border: none;
    border-top: 1px dashed #ccc;
    margin: 5px 0;
}

/* Style for course type */
.course-type {
    font-size: 0.8em;
    color: #555;
    margin-top: 2px; /* Small margin above type */
}

h3 {
    text-align: center;
    margin-top: 15px;
    margin-bottom: 15px;
    color: #333;
}
</style>
