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
                <!-- 检查 dayKey 和 period 位置是否存在且不是 null -->
                <!-- currentWeek - 1 总是 0 在单周模式下 -->
                <div v-if="processedTimetable[currentWeek -1] && processedTimetable[currentWeek-1][day] && processedTimetable[currentWeek-1][day][period]"
                     class="timetable-cell-content">
                    <!-- 修正: 遍历这个时间段内的课程条目数组 -->
                    <div v-for="item in processedTimetable[currentWeek-1][day][period]" :key="item.id">
                        <div><strong>{{ item.course_name }}</strong></div>
                        <div v-if="viewType === 'major'">{{ item.teacher_name }}</div>
                        <div v-if="viewType === 'teacher'">({{ item.major_name }})</div>
                        <div>@ {{ item.classroom_name }}</div>
                        <div class="course-type">({{ item.course_type }})</div>
                        <!-- 你可能需要添加一个分隔符，如果同一个格子有多门课的话 -->
                        <!-- <hr v-if="processedTimetable[currentWeek-1][day][period].length > 1"> -->
                    </div>
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
// TimetableGridDisplay.vue

import { ref, computed, watch } from 'vue';

const props = defineProps({
  entries: { type: Array, required: true },
  totalWeeks: { type: Number, required: true, default: 1 },
  viewType: { type: String, default: 'major' }
});

const currentWeek = ref(1); // 在 AdminStudentTimetable 场景下，这个值仍然不影响数据处理

// 直接使用后端返回的字符串作为 daysOrder
const daysOrder = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

const periodsOrder = ref([1, 2, 3, 4, 5]); // 假设 periodsOrder 中的数字对应后端返回的 entry.period

watch(() => props.totalWeeks, (newVal) => {
    if (newVal > 0 && currentWeek.value > newVal) {
        currentWeek.value = newVal;
    } else if (newVal === 0 && currentWeek.value !== 1) {
        currentWeek.value = 1;
    } else if (newVal > 0 && currentWeek.value === 0){
        currentWeek.value = 1;
    }
}, { immediate: true });


const processedTimetable = computed(() => {
  console.log("GridDisplay: Recalculating processedTimetable. Entries received:", props.entries.length);
  if (!props.entries || props.entries.length === 0) {
      console.log("GridDisplay: No entries, returning empty timetable.");
      return [];
  }

  // 初始化一个代表 *单周* 的课表结构
  // 直接使用 daysOrder 中的字符串作为 key
  const singleWeekTimetable = daysOrder.reduce((acc, day) => {
      acc[day] = periodsOrder.value.reduce((pAcc, period) => {
        pAcc[period] = null; // 初始化为空
        return pAcc;
      }, {});
      return acc;
    }, {});

  let maxPeriod = 0;
  let entriesProcessed = 0; // 添加计数器
  props.entries.forEach((entry, index) => {
    console.log(`GridDisplay: Processing entry #${index + 1}`, entry);

    // **修正**: 直接使用 entry.day_of_week 字符串作为 dayKey
    const dayKey = entry.day_of_week;

    // 检查 dayKey 是否在 daysOrder 中 (确保后端返回的字符串是预期的)
    // 同时检查 period 是否是有效的数字
    // 并且检查 period 是否在 periodsOrder 中 (如果需要过滤)
    if (daysOrder.includes(dayKey) && typeof entry.period === 'number' && entry.period > 0 && periodsOrder.value.includes(entry.period)) {

        console.log(`GridDisplay: DayKey '${dayKey}' and Period ${entry.period} are valid.`);

        // **修正**: 将数据放入 singleWeekTimetable[dayKey][entry.period]
        // 这里直接使用 dayKey 和 entry.period 作为对象的属性访问
        // 注意：如果 entry.period 是数字，它会作为数字键存储
         if (!singleWeekTimetable[dayKey]) {
             singleWeekTimetable[dayKey] = {}; // 确保 dayKey 对应的对象存在
             console.warn(`GridDisplay: Created missing day object for '${dayKey}'`); // 不太可能，因为初始化时应该都有
         }
         if (!singleWeekTimetable[dayKey][entry.period]) {
             singleWeekTimetable[dayKey][entry.period] = []; // 允许一个时间段有多个课程 (例如选修冲突)
         }

        singleWeekTimetable[dayKey][entry.period].push({ // 使用 push 添加课程，以便处理同一时间段多门课的情况
            course_name: entry.course_name,
            teacher_name: entry.teacher_name,
            major_name: entry.major_name, // 确保后端返回了这个字段
            classroom_name: entry.classroom_name,
            course_type: entry.course_type,
            // 可以保留 week_number 用于调试
            debug_week_number: entry.week_number,
            debug_day_string: entry.day_of_week, // 添加原始字符串
            debug_period_number: entry.period // 添加原始数字
        });
        entriesProcessed++;
        console.log(`GridDisplay: Placed data at ['${dayKey}'][${entry.period}]. Total courses in this slot: ${singleWeekTimetable[dayKey][entry.period].length}`);

        if (entry.period > maxPeriod) maxPeriod = entry.period;

    } else {
         console.warn(`GridDisplay: Skipping entry due to invalid day string ('${dayKey}' - in daysOrder: ${daysOrder.includes(dayKey)}) or invalid period (${entry.period}, type ${typeof entry.period} - in periodsOrder: ${periodsOrder.value.includes(entry.period)}):`, entry);
    }
  });

    // 动态调整 periodsOrder (如果需要)
   if (maxPeriod > 0 && maxPeriod > periodsOrder.value.length) {
       console.log(`GridDisplay: Max period ${maxPeriod} found, updating periodsOrder.`);
       periodsOrder.value = Array.from({length: maxPeriod}, (_, i) => i + 1);
        // 注意：这里更新 periodsOrder.value 会触发 computed 重新执行，但如果数据已经处理了，结果应该OK
        // 可能需要更复杂的逻辑来保证 periodsOrder 在处理数据前是最终的
        // 对于你的情况，periodsOrder 初始为 [1,2,3,4,5] 可能就够了，如果课程超出，需要调整这里或后端
    }

  // **修正**: 返回一个包含单周数据的数组，结构与之前兼容
  console.log(`GridDisplay: Finished processing entries. ${entriesProcessed} entries placed.`);
  console.log("GridDisplay: Final singleWeekTimetable before return:", JSON.parse(JSON.stringify(singleWeekTimetable))); // 打印最终结构
  return [singleWeekTimetable]; // 返回包含单周对象的数组

});

// formatPeriod 函数保持不变... (根据实际情况调整periodMap)
const formatPeriod = (period) => {
  const periodMap = { 1: "1-2节", 2: "3-4节", 3: "5-6节", 4: "7-8节", 5: "9-10节" }; // 根据实际情况调整
  return periodMap[period] || `第${period}大节`;
};

// prevWeek 和 nextWeek 函数保持不变
const prevWeek = () => { if (currentWeek.value > 1) currentWeek.value--; };
const nextWeek = () => { if (currentWeek.value < props.totalWeeks) currentWeek.value++; };



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
  td {
    transition: all 0.2s ease; /* 平滑过渡效果 */

    &:hover {
      background-color: #f8f9fa; /* 悬停背景色 */
      transform: translateY(-2px); /* 轻微上浮效果 */
      box-shadow: 0 2px 8px rgba(0,0,0,0.1); /* 悬停阴影 */
    }
  }
}

.timetable-grid th{
  border: 1px solid #ccc;
  padding: 8px;
  text-align: center;
  min-width: 115px; /* Minimum width for content */
  height: 30px; /* Fixed height for cells */
  vertical-align: top;
}
.timetable-grid td {
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
