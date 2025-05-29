<template>
  <div class="admin-dashboard-layout">
    <aside class="sidebar">
      <h2>管理员功能</h2>
      <nav>
        <ul>
          <li class="sidebar-menu-item">
            <router-link to="/admin/import-course-plan" active-class="active-link">课程计划</router-link>
          </li>
          <li class="sidebar-menu-item">
            <router-link to="/admin/teacher-timetable" active-class="active-link">查询教员课表</router-link>
          </li>
          <li class="sidebar-menu-item">
            <router-link to="/admin/student-timetable" active-class="active-link">查询学生课表</router-link>
          </li>
          <li class="sidebar-menu-item">
            <router-link to="/admin/manual-scheduling" active-class="active-link">手动调整课表</router-link>
          </li>
          <!-- 根据您提供的图片，还有其他管理模块，可以在这里添加 -->

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
  loggedInUsername.value = localStorage.getItem('username') || '管理员用户'; // 假设管理员用户名存储在username
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
.admin-dashboard-layout {
  display: flex;
  min-height: 100vh;
  background-color: #f8f9fa;
}

.sidebar {
  width: 250px;
  background-color: #343a40; /* 深色背景 */
  color: white;
  padding: 20px;
  box-shadow: 2px 0 5px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.sidebar h2 {
  color: #007bff;
  margin-bottom: 30px;
  text-align: center;
}

.sidebar nav ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.sidebar nav ul li {
  margin-bottom: 5px; /* 减小列表项间距 */
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
  background-color: #007bff;
}

.sidebar-menu-category {
    color: #adb5bd; /* 类别标题颜色 */
    font-size: 0.8em;
    padding: 10px 15px 5px;
    margin-top: 15px;
    text-transform: uppercase; /* 大写 */
    border-bottom: 1px solid #495057; /* 分割线 */
    margin-bottom: 10px;
}

.user-info {
  margin-top: auto;
  padding-top: 20px;
  border-top: 1px solid #495057;
  text-align: center;
}

.user-info p {
  margin-bottom: 15px;
  font-size: 0.9em;
  color: #adb5bd;
}

.logout-button {
  width: 100%;
  padding: 10px 15px;
  background-color: #dc3545;
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
  flex-grow: 1;
  padding: 30px;
  background-color: #fff;
  box-shadow: 0 0 10px rgba(0,0,0,0.05);
  margin: 20px;
  border-radius: 8px;
}
</style>
