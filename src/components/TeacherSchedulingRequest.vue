<template>
  <div class="page-content">
    <h2>教师排课要求</h2>
    <!-- 教师提出排课要求/变更申请的区域 -->
    <div class="request-section">
      <h3>提出新的时间偏好</h3>
      <p>您可以在这里提出希望<strong>避免</strong>或<strong>优先</strong>安排课程的时间段。请在管理员设置排课计划前提交。</p>
      <!-- 按钮触发模态框 -->
      <button class="open-modal-button" @click="openRequestModal">提出新的时间偏好</button>
    </div>

    <!-- 显示已提交的偏好列表 -->
    <div class="preferences-list-section">
       <h3>我已提交的时间偏好</h3>
       <p v-if="isPreferencesLoading">加载中...</p>
       <p v-else-if="preferencesError" class="error-message">{{ preferencesError }}</p>
       <p v-else-if="teacherPreferences.length === 0">您还没有提交任何时间偏好。</p>

       <ul v-else class="preferences-list">
          <li v-for="pref in teacherPreferences" :key="pref.id" class="preference-item">
             <div class="preference-details">
                <span class="semester-name">{{ pref.semester_name }}</span>
                <span class="timeslot-info">
                   {{ pref.day_of_week_display }} 第 {{ pref.period }} 节 ({{ pref.start_time }} - {{ pref.end_time }})
                </span>
                <span :class="['preference-type', pref.preference_type]">{{ pref.preference_type_display }}</span>
             </div>
             <div class="preference-status">
                状态: <span :class="['status', pref.status]">{{ pref.status_display }}</span>
             </div>
             <div v-if="pref.reason" class="preference-reason">
                原因: {{ pref.reason }}
             </div>
              <div class="preference-timestamps">
                  提交时间: {{ pref.created_at_formatted }}
              </div>
              <!-- --- New Delete Button --- -->
              <div class="preference-actions">
                  <button
                      class="delete-button"
                      @click="confirmDeletePreference(pref.id)"
                      :disabled="isDeleting[pref.id]"
                      :title="isDeleting[pref.id] ? '删除中...' : '删除此偏好'"
                  >
                       {{ isDeleting[pref.id] ? '删除中...' : '删除' }}
                  </button>
              </div>
              <!-- --- End Delete Button --- -->
          </li>
       </ul>
       <p v-if="deleteMessage" :class="{'message': true, 'error': isDeleteError}">{{ deleteMessage }}</p>
    </div>


    <!-- 排课要求/变更申请模态框 -->
    <div v-if="isModalVisible" class="modal-overlay" @click.self="closeRequestModal">
      <div class="modal-content">
        <h3>提交时间偏好</h3>
        <form @submit.prevent="handleSubmitPreference">

          <div class="form-group">
             <label for="semester-select">选择学期:</label>
             <select id="semester-select" v-model="selectedSemesterId" required>
               <option value="" disabled>请选择学期</option>
               <option v-for="semester in semesters" :key="semester.id" :value="semester.id">
                 {{ semester.name }}
               </option>
             </select>
           </div>

          <!-- 专注于时间/日期偏好 -->
          <div>
             <h4>选择时间段</h4>
              <div class="form-group">
                 <label for="timeslot-select">日期/节次:</label>
                 <select id="timeslot-select" v-model="selectedTimeslotId" required>
                    <option value="" disabled>请选择日期和节次</option>
                    <option v-for="ts in availableTimeSlots" :key="ts.id" :value="ts.id">
                       {{ ts.day_of_week }} 第 {{ ts.period }} 节 ({{ ts.start_time }} - {{ ts.end_time }})
                    </option>
                 </select>
              </div>

              <div class="form-group">
                <label for="preference-type">偏好类型:</label>
                 <select id="preference-type" v-model="preferenceType" required>
                    <option value="avoid">避免安排</option>
                    <!-- <option value="prefer">优先安排</option> -->
                 </select>
              </div>
          </div>

          <div class="form-group">
            <label for="request-reason">原因 (可选):</label>
            <textarea id="request-reason" v-model="requestReason" placeholder="请详细描述您的原因..." rows="4"></textarea>
          </div>

          <div class="modal-actions">
            <button type="submit" :disabled="isLoading">提交偏好</button>
            <button type="button" class="cancel-button" @click="closeRequestModal" :disabled="isLoading">取消</button>
          </div>
        </form>
        <p v-if="requestMessage" :class="{'message': true, 'error': isError}">{{ requestMessage }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// 模态框状态
const isModalVisible = ref(false);
const isLoading = ref(false); // Loading state for submitting new preference
const isPreferencesLoading = ref(false); // Loading state for fetching preferences list
const isError = ref(false); // To style message as error for form submission
const preferencesError = ref(null); // Error message for fetching preferences list

// Data for list and form
const loggedInUserId = ref(null);
const semesters = ref([]);
const availableTimeSlots = ref([]);
const teacherPreferences = ref([]);

// Form data
const selectedSemesterId = ref('');
const selectedTimeslotId = ref('');
const preferenceType = ref('avoid');
const requestReason = ref('');

// Submission feedback
const requestMessage = ref('');
const deleteMessage = ref(''); // Message specifically for delete operations
const isDeleteError = ref(false); // To style delete message as error

// State for delete operations - track which item is being deleted
const isDeleting = ref({}); // Use an object to store loading state per preference ID


onMounted(async () => {
   const storedUserId = localStorage.getItem('user_id');
   const storedUserRole = localStorage.getItem('userRole');

   if (storedUserId && storedUserRole && storedUserRole.toLowerCase() === 'teacher') {
       loggedInUserId.value = Number(storedUserId);
       console.log(`Teacher Scheduling Request: User ID ${loggedInUserId.value} (Role: ${storedUserRole}) logged in.`);
       await fetchSemesters();
       await fetchTimeSlots();
       await fetchTeacherPreferences(loggedInUserId.value);
   } else {
       console.error('Teacher Scheduling Request: Invalid or missing user ID/role in localStorage.');
        preferencesError.value = '未能获取有效的教师登录信息，无法加载偏好列表。';
        requestMessage.value = '未能获取有效的教师登录信息，请尝试重新登录。';
        isError.value = true;
   }
});


const fetchSemesters = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    semesters.value = response.data;
  } catch (error) {
    console.error('Error fetching semesters:', error);
     requestMessage.value = '无法加载学期信息。';
     isError.value = true;
  }
};

const fetchTimeSlots = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/time-slots`);
    availableTimeSlots.value = response.data;
    console.log('Fetched Time Slots:', availableTimeSlots.value);
  } catch (error) {
    console.error('Error fetching time slots:', error);
     requestMessage.value = '无法加载时间段信息。';
     isError.value = true;
  }
};

const fetchTeacherPreferences = async (userId) => {
    if (!userId) {
        preferencesError.value = '无法获取用户ID，无法加载偏好列表。';
        return;
    }
    isPreferencesLoading.value = true;
    preferencesError.value = null;

    try {
        // Pass user_id as a query parameter for verification in DELETE API (Temporary)
        // Replace with your secure method of obtaining user_id in backend DELETE API
        const response = await axios.get(`${API_BASE_URL}/api/teacher/${userId}/scheduling-preferences`);
        teacherPreferences.value = response.data;
        console.log('Fetched Teacher Preferences:', teacherPreferences.value);
        // Initialize isDeleting state for all preferences
        teacherPreferences.value.forEach(pref => {
            isDeleting.value[pref.id] = false;
        });

    } catch (error) {
        console.error('Error fetching teacher preferences:', error);
        if (error.response) {
            preferencesError.value = error.response.data.message || `加载偏好列表失败: ${error.response.statusText}`;
        } else {
            preferencesError.value = '加载偏好列表时发生网络错误或服务器无响应。';
        }
    } finally {
        isPreferencesLoading.value = false;
    }
};

const openRequestModal = () => {
  if (loggedInUserId.value === null) {
      requestMessage.value = '请先登录教师账号再提出要求。';
      isError.value = true;
      return;
  }
   if (semesters.value.length === 0 || availableTimeSlots.value.length === 0) {
        requestMessage.value = '学期或时间段信息正在加载中，请稍候再试。';
        isError.value = true;
       return;
   }

  isModalVisible.value = true;
  resetPreferenceForm();
  requestMessage.value = ''; // Clear form submission message
  isError.value = false;
};

const closeRequestModal = () => {
  isModalVisible.value = false;
  resetPreferenceForm();
  requestMessage.value = '';
  isError.value = false;
};

const resetPreferenceForm = () => {
    selectedSemesterId.value = '';
    selectedTimeslotId.value = '';
    preferenceType.value = 'avoid';
    requestReason.value = '';
}

const handleSubmitPreference = async () => {
  if (loggedInUserId.value === null) {
       requestMessage.value = '无法获取您的用户ID，请重新登录。';
       isError.value = true;
       return;
  }

  isLoading.value = true;
  requestMessage.value = '';
  isError.value = false;
  deleteMessage.value = ''; // Clear delete messages

  const preferenceData = {
      user_id: loggedInUserId.value, // Send user ID (needed for some backend auth/logic)
      semester_id: selectedSemesterId.value,
      timeslot_id: selectedTimeslotId.value,
      preference_type: preferenceType.value.toLowerCase(),
      reason: requestReason.value,
  };

  console.log('提交教师时间偏好:', preferenceData);

  try {
    const response = await axios.post(`${API_BASE_URL}/api/teacher/scheduling-preferences`, preferenceData);

    requestMessage.value = response.data.message || '时间偏好已提交成功！';
    isError.value = false;

    await fetchTeacherPreferences(loggedInUserId.value); // Refresh list

  } catch (error) {
     console.error('Submit preference error:', error);
     isError.value = true;

     if (error.response) {
         requestMessage.value = error.response.data.error || error.response.data.message || `提交偏好失败: ${error.response.statusText}`;
         if (error.response.status === 400 && error.response.data.message && error.response.data.message.includes("数据完整性错误")) {
             requestMessage.value += " (您可能已为该学期该时段提交过同类偏好)";
         }

     } else {
         requestMessage.value = '提交偏好时发生网络错误或服务器无响应。';
     }
  } finally {
     isLoading.value = false;
  }
};

// --- New Delete Functions ---

// Confirmation dialog before deleting
const confirmDeletePreference = (preferenceId) => {
    if (confirm('确定要删除此排课时间偏好吗？')) {
        deletePreference(preferenceId);
    }
}

// Send DELETE request to backend
const deletePreference = async (preferenceId) => {
    if (loggedInUserId.value === null) {
       deleteMessage.value = '无法获取您的用户ID，请重新登录。';
       isDeleteError.value = true;
       return;
    }

    isDeleting.value[preferenceId] = true; // Set loading state for this specific item
    deleteMessage.value = ''; // Clear previous delete message
    isDeleteError.value = false;

    console.log('尝试删除偏好:', preferenceId);

    try {
        // Call the backend DELETE API.
        // IMPORTANT: Pass user_id securely for backend verification.
        // For this example, adding user_id as a query param (LESS SECURE).
        // Replace with passing user_id via token/session or header if using auth middleware.
        const response = await axios.delete(`${API_BASE_URL}/api/teacher/scheduling-preferences/${preferenceId}`, {
            params: { user_id: loggedInUserId.value } // UNSAFE: Use secure method in production
            // Or if using headers with middleware: { headers: { 'X-User-ID': loggedInUserId.value } }
        });

        deleteMessage.value = response.data.message || '偏好删除成功！';
        isDeleteError.value = false;

        // --- Remove the deleted item from the list directly or refetch ---
        // Option 1: Remove from list (faster UI update)
        teacherPreferences.value = teacherPreferences.value.filter(pref => pref.id !== preferenceId);

        // Option 2: Refetch the entire list (more robust for complex scenarios)
        // await fetchTeacherPreferences(loggedInUserId.value);
        // --- End Remove ---

    } catch (error) {
        console.error('Delete preference error:', error);
        isDeleteError.value = true;

        if (error.response) {
            deleteMessage.value = error.response.data.error || error.response.data.message || `删除偏好失败: ${error.response.statusText}`;
        } else {
            deleteMessage.value = '删除偏好时发生网络错误或服务器无响应。';
        }
    } finally {
        isDeleting.value = { ...isDeleting.value, [preferenceId]: false }; // Reset loading state for this item
        // Or clear all if refetching: isDeleting.value = {};
    }
};
// --- End Delete Functions ---

</script>

<style scoped>
/* Keep previous styles, add styles for delete button */
.page-content {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

h2 {
  text-align: center;
  color: #333;
  margin-bottom: 20px;
}

.request-section, .preferences-list-section {
  margin-top: 20px;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 8px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.request-section h3, .preferences-list-section h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #007bff;
}

.request-section p {
    margin-bottom: 15px;
    color: #555;
}

.open-modal-button {
  display: inline-block;
  padding: 10px 18px;
  background-color: #28a745; /* Green button */
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s ease;
}
.open-modal-button:hover {
  background-color: #218838;
}

/* Preferences List Styles */
.preferences-list-section {
    margin-top: 30px;
}

.preferences-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.preference-item {
    background-color: #f9f9f9;
    border: 1px solid #eee;
    border-radius: 6px;
    padding: 15px;
    margin-bottom: 15px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    display: flex; /* Use flexbox for layout */
    flex-wrap: wrap; /* Allow items to wrap */
    justify-content: space-between; /* Distribute space */
    align-items: center; /* Vertically center items */
}

.preference-details {
    font-size: 1.1em;
    /* margin-bottom: 8px; Removed margin-bottom for flex layout */
    color: #333;
    flex-grow: 1; /* Allow details to take available space */
    margin-right: 10px; /* Space between details and actions */
}

.semester-name {
    font-weight: bold;
    margin-right: 10px;
    color: #0056b3;
}

.timeslot-info {
    margin-right: 10px;
    color: #555;
}

.preference-type {
    font-weight: bold;
    padding: 3px 8px;
    border-radius: 3px;
    font-size: 0.9em;
    white-space: nowrap; /* Prevent text wrapping */
}

.preference-type.avoid {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

.preference-type.prefer {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}

.preference-status {
    font-size: 0.9em;
    color: #666;
    /* margin-bottom: 5px; Removed margin-bottom */
    flex-basis: 100%; /* Make status take full width on next line */
    margin-top: 8px; /* Add space above status if it wraps */
}

.status {
    font-weight: bold;
}

.status.pending { color: #ffc107; }
.status.approved { color: #28a745; }
.status.rejected { color: #dc3545; }
.status.applied { color: #17a2b8; }


.preference-reason {
    font-size: 0.9em;
    color: #777;
    font-style: italic;
    margin-top: 5px;
    padding-top: 5px;
    border-top: 1px dashed #eee;
    flex-basis: 100%; /* Make reason take full width */
}

.preference-timestamps {
     font-size: 0.8em;
     color: #999;
     margin-top: 8px;
     flex-basis: 100%; /* Make timestamps take full width */
}

/* --- New Actions Section Style --- */
.preference-actions {
    flex-shrink: 0; /* Prevent shrinking */
    margin-left: auto; /* Space from details */
    display: flex; /* Use flex to align buttons if multiple */
    align-items: flex-start;
}

.delete-button {
    padding: 5px 10px;
    background-color: #dc3545; /* Red */
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9em;
    transition: background-color 0.3s ease, opacity 0.3s ease;

}

.delete-button:hover:not(:disabled) {
    background-color: #c82333;
}

.delete-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}
/* --- End New Actions Section Style --- */


/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: #fff;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  max-width: 450px;
  width: 90%;
  max-height: 85vh;
  overflow-y: auto;
  position: relative;
}

.modal-content h3 {
  margin-top: 0;
  margin-bottom: 20px;
  text-align: center;
  color: #333;
  font-size: 1.5em;
}

.form-group {
  margin-bottom: 18px;
}

label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
  color: #555;
  font-size: 1em;
}

input[type="text"],
select,
textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-sizing: border-box;
  font-size: 1em;
}

textarea {
    resize: vertical;
}

.modal-actions {
  margin-top: 30px;
  text-align: right;
}

.modal-actions button {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
  margin-left: 10px;
  transition: background-color 0.3s ease, opacity 0.3s ease;
}

.modal-actions button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.modal-actions button[type="submit"] {
  background-color: #007bff;
  color: white;
}

.modal-actions button[type="submit"]:hover:not(:disabled) {
  background-color: #0056b3;
}

.modal-actions .cancel-button {
  background-color: #6c757d;
  color: white;
}

.modal-actions .cancel-button:hover:not(:disabled) {
  background-color: #5a6268;
}

/* Messages */
.message {
    margin-top: 20px;
    padding: 10px;
    text-align: center;
    font-size: 1em;
    border-radius: 4px;
    color: #155724;
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
}

.message.error, .error-message {
    color: #721c24;
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
}
.error-message {
    margin-top: 15px;
    padding: 10px;
    text-align: center;
    font-size: 1em;
    border-radius: 4px;
}
</style>
