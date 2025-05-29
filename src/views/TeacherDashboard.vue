<template>
  <div class="teacher-dashboard-layout">
    <aside class="sidebar">
      <h2>教师功能</h2>
      <nav>
        <ul>
          <li><router-link to="/teacher/timetable" active-class="active-link">查询课表</router-link></li>
          <li><router-link to="/teacher/class-members" active-class="active-link">查询班级人员</router-link></li>
          <li><router-link to="/teacher/scheduling-request" active-class="active-link">提出排课要求</router-link></li>
        </ul>
      </nav>
      <div class="user-info">
        <p>欢迎您，{{ loggedInUsername }}！</p>
        <button @click="logout" class="logout-button">退出登录</button>
      </div>
    </aside>

    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const loggedInUsername = ref('');

onMounted(() => {
  loggedInUsername.value = localStorage.getItem('username') || '教师用户';
});

const logout = () => {
  // 清除用户登录状态和用户名
  localStorage.removeItem('token');
  localStorage.removeItem('userRole');
  localStorage.removeItem('username');
  router.push('/login'); // 跳转回登录页面
};
</script>

<style scoped>
.teacher-dashboard-layout {
  display: flex;
  min-height: 100vh; /* 确保整个页面高度 */
  background-color: #f8f9fa; /* 轻微的背景色 */
}

.sidebar {
  width: 250px;
  background-color: #343a40; /* 深色背景 */
  color: white;
  padding: 20px;
  box-shadow: 2px 0 5px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  justify-content: space-between; /* 将用户信息推到底部 */
}

.sidebar h2 {
  color: #007bff; /* 蓝色强调色 */
  margin-bottom: 30px;
  text-align: center;
}

.sidebar nav ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.sidebar nav ul li {
  margin-bottom: 10px;
}

.sidebar nav ul li a {
  display: block;
  color: white;
  text-decoration: none;
  padding: 10px 15px;
  border-radius: 4px;
  transition: background-color 0.3s ease;
}

.sidebar nav ul li a:hover,
.sidebar nav ul li a.active-link {
  background-color: #007bff; /* 选中或悬停时的背景色 */
}

.user-info {
  margin-top: auto; /* 自动将此部分推到底部 */
  padding-top: 20px;
  border-top: 1px solid #495057; /* 分隔线 */
  text-align: center;
}

.user-info p {
  margin-bottom: 15px;
  font-size: 0.9em;
  color: #adb5bd; /* 较浅的文本颜色 */
}

.logout-button {
  width: 100%;
  padding: 10px 15px;
  background-color: #dc3545; /* 红色表示危险操作 */
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
  transition: background-color 0.3s ease;
}

.logout-button:hover {
  background-color: #c82333;
}

.main-content {
  flex-grow: 1; /* 占据剩余空间 */
  padding: 30px;
  background-color: #fff;
  box-shadow: 0 0 10px rgba(0,0,0,0.05); /* 轻微阴影 */
  margin: 20px; /* 与侧边栏和页面边缘的间距 */
  border-radius: 8px; /* 圆角 */
}
</style>
