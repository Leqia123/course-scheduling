<template>
  <div class="page-content">
    <h2>提出排课要求</h2>
    <!-- 教师提出排课要求/变更申请的区域 -->
    <div class="request-section">
      <h3>排课要求与申请</h3>
      <!-- 按钮触发模态框 -->
      <button class="open-modal-button" @click="openRequestModal">提出新的要求/申请</button>

      <!-- 显示已提交的申请列表（可选，如果需要的话） -->
      <!-- <h4>我的申请记录</h4> -->
      <!-- TODO: 在这里加载并显示教师已提交的申请列表 -->
      <!-- <p>(申请记录显示区域)</p> -->
    </div>

    <!-- 排课要求/变更申请模态框 -->
    <div v-if="isModalVisible" class="modal-overlay" @click.self="closeRequestModal">
      <div class="modal-content">
        <h3>提交排课要求/申请</h3>
        <form @submit.prevent="handleSubmitRequest">

          <div class="form-group">
            <label for="request-type">申请类型:</label>
            <select id="request-type" v-model="requestType" required>
              <option value="" disabled>请选择申请类型</option>
              <option value="modify_existing">修改现有排课</option>
              <option value="time_constraint">时间/日期偏好或限制</option>
              <!-- TODO: 可以添加更多类型，例如：申请新增排课 -->
            </select>
          </div>

          <!-- 根据申请类型显示不同的表单字段 -->
          <div v-if="requestType === 'modify_existing'">
            <h4>修改现有排课</h4>
            <div class="form-group">
              <label for="select-schedule">选择要修改的排课:</label>
              <select id="select-schedule" v-model="selectedScheduleId" required>
                <option value="" disabled>请选择一条排课记录</option>
                <!-- TODO: 这里需要从后端加载当前教师的排课列表 -->
                <option v-for="schedule in teacherSchedules" :key="schedule.id" :value="schedule.id">
                  {{ schedule.course_name }} ({{ schedule.day }} {{ schedule.time }} @ {{ schedule.classroom }})
                </option>
              </select>
            </div>

            <div class="form-group">
              <label for="change-type">修改内容:</label>
              <select id="change-type" v-model="changeType" required>
                 <option value="" disabled>请选择修改内容</option>
                 <option value="classroom">更换教室</option>
                 <option value="time">更换时间/节次</option>
                 <option value="day">更换日期/周</option>
                 <!-- TODO: 可以添加更多修改内容，例如：更换教师（需要与管理员协商） -->
              </select>
            </div>

             <div class="form-group" v-if="changeType">
                <!-- 根据修改内容，这里的输入框类型可能不同 -->
                <label for="new-value">新的{{ changeType === 'classroom' ? '教室' : changeType === 'time' ? '时间/节次' : '日期/周' }}:</label>
                <!-- 简化示例：使用文本输入框。实际应用中应根据 changeType 使用下拉框/日期时间选择器 -->
                 <input v-if="changeType !== 'classroom'" type="text" id="new-value" v-model="newValue" :placeholder="'请输入新的' + (changeType === 'classroom' ? '教室' : changeType === 'time' ? '时间/节次' : '日期/周')" required>

                 <!-- 教室选择使用下拉框 -->
                 <select v-if="changeType === 'classroom'" id="new-value-classroom" v-model="newValue" required>
                     <option value="" disabled>请选择新的教室</option>
                     <!-- TODO: 这里需要从后端加载可用的教室列表 -->
                     <option v-for="room in availableClassrooms" :key="room.id" :value="room.id">{{ room.name }}</option>
                 </select>

            </div>
          </div>

          <div v-if="requestType === 'time_constraint'">
             <h4>时间/日期偏好或限制</h4>
              <div class="form-group">
                <label for="constraint-day">日期/周:</label>
                 <select id="constraint-day" v-model="constraintDay" required>
                    <option value="" disabled>请选择日期/周</option>
                    <option v-for="day in availableDays" :key="day" :value="day">{{ day }}</option>
                 </select>
              </div>
               <div class="form-group">
                <label for="constraint-time">时间/节次:</label>
                 <select id="constraint-time" v-model="constraintTime" required>
                    <option value="" disabled>请选择时间/节次</option>
                    <option v-for="time in availableTimes" :key="time" :value="time">{{ time }}</option>
                 </select>
              </div>
              <div class="form-group">
                <label for="constraint-type">偏好/限制类型:</label>
                 <select id="constraint-type" v-model="constraintType" required>
                    <option value="avoid">避免安排</option>
                    <option value="prefer">优先安排</option>
                 </select>
              </div>
          </div>

          <div class="form-group">
            <label for="request-reason">原因:</label>
            <textarea id="request-reason" v-model="requestReason" placeholder="请详细描述您的原因..." rows="4" required></textarea>
          </div>

          <div class="modal-actions">
            <button type="submit">提交申请</button>
            <button type="button" class="cancel-button" @click="closeRequestModal">取消</button>
          </div>
        </form>
        <p v-if="requestMessage" class="message">{{ requestMessage }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
// 此组件不再直接处理路由跳转和用户登录信息，这些由父组件 TeacherDashboard 处理
// import { useRouter } from 'vue-router'; // 移除

// 模态框状态
const isModalVisible = ref(false);

// 申请表单数据
const requestType = ref(''); // 申请类型
const selectedScheduleId = ref(null); // 修改现有排课时选中排课的ID
const changeType = ref(''); // 修改现有排课时修改的内容类型
const newValue = ref(''); // 修改现有排课时的新值
const constraintDay = ref(''); // 时间限制：日期
const constraintTime = ref(''); // 时间限制：时间
const constraintType = ref('avoid'); // 时间限制：类型 (avoid/prefer)
const requestReason = ref(''); // 申请原因

// 模拟数据，实际应从后端获取
const teacherSchedules = ref([
    { id: 1, course_name: '高等数学A', day: '周一', time: '第三节', classroom: '教学楼A101' },
    { id: 2, course_name: '大学物理', day: '周三', time: '第一节', classroom: '教学楼B202' },
    { id: 3, course_name: '数据结构', day: '周五', time: '第五节', classroom: '实验楼C303' },
]);
const availableDays = ref(['周一', '周二', '周三', '周四', '周五']);
const availableTimes = ref(['第一/二节','第三/四节', '第五/六节','第七/八节']);
const availableClassrooms = ref([
    { id: 101, name: '教学楼A101' },
    { id: 102, name: '教学楼A102' },
    { id: 201, name: '教学楼B201' },
    { id: 202, name: '教学楼B202' },
    { id: 303, name: '实验楼C303' },
]);

const requestMessage = ref(''); // 提交申请后的反馈信息

// 在组件挂载后执行 (此处不再需要获取用户名，专注于表单相关的数据获取)
onMounted(() => {
  // TODO: 在这里调用后端API获取教师课表数据和已提交的申请列表
  // fetchTeacherTimetable(); // 如果需要在这里显示已提交的申请，可以调用
  // fetchTeacherRequests();
  // TODO: 如果是修改现有排课，还需要调用API获取 teacherSchedules 列表
  // fetchTeacherSchedulesData();
  // TODO: 如果需要选择新的教室，还需要调用API获取 availableClassrooms 列表
  // fetchAvailableClassroomsData();
});

const openRequestModal = () => {
  isModalVisible.value = true;
  resetRequestForm(); // 打开时重置表单
};

const closeRequestModal = () => {
  isModalVisible.value = false;
  resetRequestForm(); // 关闭时重置表单
  requestMessage.value = ''; // 清空反馈信息
};

const resetRequestForm = () => {
    requestType.value = '';
    selectedScheduleId.value = null;
    changeType.value = '';
    newValue.value = '';
    constraintDay.value = '';
    constraintTime.value = '';
    constraintType.value = 'avoid';
    requestReason.value = '';
}

const handleSubmitRequest = () => {
  requestMessage.value = ''; // 清空之前的反馈信息

  // TODO: 在这里调用后端API提交申请
  // 收集表单数据
  const requestData = {
      type: requestType.value,
      reason: requestReason.value,
      // 根据申请类型添加其他字段
      ...(requestType.value === 'modify_existing' && {
          schedule_id: selectedScheduleId.value,
          change_type: changeType.value,
          new_value: newValue.value, // 注意这里，实际应根据 changeType 发送不同格式的数据
      }),
      ...(requestType.value === 'time_constraint' && {
          day_of_week: constraintDay.value,
          time_slot: constraintTime.value,
          constraint_type: constraintType.value,
      }),
      // TODO: 可能还需要提交当前教师的用户ID
      // teacher_id: /* 获取当前教师ID */
  };

  console.log('提交教师申请:', requestData);

  // 模拟提交成功或失败
  // axios.post('/api/teacher_requests', requestData)
  //   .then(response => {
        requestMessage.value = '申请已提交成功！等待管理员审核。';
        // closeRequestModal(); // 提交成功后关闭模态框
        // TODO: 刷新教师的申请记录列表
  //   })
  //   .catch(error => {
  //      requestMessage.value = error.response?.data?.message || '提交申请失败，请稍后重试。';
  //      console.error('Submit request error:', error);
  //   });

  // 模拟成功
  setTimeout(() => { // 模拟网络延迟
      requestMessage.value = '模拟申请已提交成功！';
      // closeRequestModal(); // 模拟提交成功后关闭模态框 (可选)
  }, 1000);
};

// TODO: 函数用于从后端获取数据 (teacherSchedules, availableClassrooms 等)
// async function fetchTeacherSchedulesData() {
//    try {
//       const response = await axios.get('/api/teacher/schedules', { /* auth header */ });
//       teacherSchedules.value = response.data;
//    } catch (error) {
//       console.error('Failed to fetch teacher schedules:', error);
//    }
// }
// async function fetchAvailableClassroomsData() { /* ... */ }
</script>

<style scoped>
/* 确保这里的样式与您原代码中的完全一致，仅移除原 .teacher-container 和 logout 按钮相关的样式 */
.page-content {
  padding: 20px; /* 为子页面内容提供一些内边距 */
}
.request-section {
  margin-top: 30px;
  border-top: 1px solid #eee;
  padding-top: 20px;
}
.request-section h3 {
    margin-bottom: 15px;
}
.open-modal-button {
  display: inline-block; /* 确保按钮在行内 */
  padding: 10px 15px;
  background-color: #007bff; /* 使用主题色 */
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s ease;
}
.open-modal-button:hover {
  background-color: #0056b3;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6); /* 半透明黑色背景 */
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000; /* 确保在最上层 */
}

.modal-content {
  background-color: #fff;
  padding: 30px; /* 增加内边距 */
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  max-width: 500px; /* 最大宽度 */
  width: 90%; /* 响应式宽度 */
  max-height: 80vh; /* 最大高度，防止内容过多溢出 */
  overflow-y: auto; /* 内容过多时允许垂直滚动 */
  position: relative; /* 为了方便定位关闭按钮（如果需要） */
}

.modal-content h3 {
  margin-top: 0;
  margin-bottom: 20px;
  text-align: center;
  color: #333;
}

.form-group {
  margin-bottom: 15px; /* 减小一些间距，让表单更紧凑 */
}

label {
  display: block;
  margin-bottom: 6px; /* 减小一些间距 */
  font-weight: bold;
  color: #555;
  font-size: 14px; /* 字体稍小 */
}

input[type="text"],
select,
textarea {
  width: 100%;
  padding: 8px; /* 减小内边距 */
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
  font-size: 14px; /* 字体稍小 */
}

textarea {
    resize: vertical; /* 允许垂直调整大小 */
}


.modal-actions {
  margin-top: 25px; /* 增加顶部间距 */
  text-align: right; /* 按钮靠右对齐 */
}

.modal-actions button {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 15px;
  margin-left: 10px; /* 按钮之间留白 */
  transition: background-color 0.3s ease;
}

.modal-actions button[type="submit"] {
  background-color: #28a745; /* 绿色表示提交 */
  color: white;
}

.modal-actions button[type="submit"]:hover {
  background-color: #218838;
}

.modal-actions .cancel-button {
  background-color: #6c757d; /* 灰色表示取消 */
  color: white;
}

.modal-actions .cancel-button:hover {
  background-color: #5a6268;
}

.message {
    margin-top: 15px;
    text-align: center;
    font-size: 14px;
    color: green; /* 成功消息 */
}
/* 如果有错误消息，可以单独设置颜色 */
/* .message.error { color: red; } */
</style>
