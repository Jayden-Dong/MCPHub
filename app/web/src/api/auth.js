import axios from 'axios'

const authApi = axios.create({
  baseURL: '/api/auth',
  timeout: 30000,
})

// 响应拦截器
authApi.interceptors.response.use(
  (response) => response.data,
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * 用户登录
 * @param {string} username 用户名
 * @param {string} password 密码
 * @returns {Promise<{access_token: string, token_type: string, user: object}>}
 */
export async function login(username, password) {
  return authApi.post('/login', { username, password })
}

/**
 * 用户登出
 */
export async function logout() {
  return authApi.post('/logout')
}

/**
 * 获取当前用户信息
 */
export async function getCurrentUser() {
  return authApi.get('/me')
}

/**
 * 修改密码
 * @param {string} oldPassword 原密码
 * @param {string} newPassword 新密码
 */
export async function changePassword(oldPassword, newPassword) {
  return authApi.post('/password', {
    old_password: oldPassword,
    new_password: newPassword
  })
}

// ========== 管理员接口 ==========

/**
 * 获取用户列表
 */
export async function getUsers() {
  return authApi.get('/users')
}

/**
 * 注册新用户
 * @param {string} username 用户名
 * @param {string} password 密码
 */
export async function registerUser(username, password) {
  return authApi.post('/register', { username, password })
}

/**
 * 切换用户状态
 * @param {number} userId 用户ID
 * @param {boolean} isActive 是否激活
 */
export async function toggleUserStatus(userId, isActive) {
  return authApi.put(`/users/${userId}/status?is_active=${isActive}`)
}

/**
 * 删除用户
 * @param {number} userId 用户ID
 */
export async function deleteUser(userId) {
  return authApi.delete(`/users/${userId}`)
}

/**
 * 重置用户密码
 * @param {number} userId 用户ID
 * @param {string} newPassword 新密码
 */
export async function resetUserPassword(userId, newPassword) {
  return authApi.put(`/users/${userId}/password?new_password=${encodeURIComponent(newPassword)}`, null)
}