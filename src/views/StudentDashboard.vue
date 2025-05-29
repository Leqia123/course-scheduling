<template>
  <div class="student-container">
    <!-- 将硬编码的用户类型文本替换为动态绑定的用户名 -->
    <h2>学生课表</h2>
    <p>欢迎您，{{ loggedInUsername }}！</p> <!-- 修改这里 -->
    <div class="timetable-placeholder">
      <!-- TODO: 在这里显示学生的课表 -->
      <p>您的课表将在这里展示。</p>
      <p>(开发中...)</p>
    </div>
    <button @click="logout">退出登录</button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'; // 导入 ref 和 onMounted
import { useRouter } from 'vue-router';

const router = useRouter();
const loggedInUsername = ref(''); // 添加一个 ref 来存储用户名

// 在组件挂载后执行
onMounted(() => {
  // 从 localStorage 中读取用户名
  loggedInUsername.value = localStorage.getItem('username') || '学生用户'; // 如果没有找到，显示默认值
});

const logout = () => {
  // 清除用户登录状态和用户名
  localStorage.removeItem('token');
  localStorage.removeItem('userRole');
  localStorage.removeItem('username'); // <-- 添加这行
  router.push('/login');
};

// TODO: 在组件加载时调用后端API获取学生课表数据
// 例如: onMounted(() => { fetchStudentTimetable(); });
// function fetchStudentTimetable() { /* axios.get('/api/timetable/student/...') */ }
</script>

<style scoped>
/* ... 样式保持不变 ... */
.student-container {
  padding: 20px;
}
.timetable-placeholder {
  border: 1px dashed #ccc;
  padding: 20px;
  text-align: center;
  margin-top: 20px;
  min-height: 200px;
}
button {
    margin-top: 20px;
    padding: 10px 15px;
    background-color: #f44336;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}
button:hover {
    background-color: #d32f2f;
}
</style>
