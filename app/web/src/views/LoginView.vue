<template>
  <div class="login-container">
    <!-- 动态背景层 -->
    <div class="bg-layer">
      <!-- 主视觉SVG - 思考到行动的转换 -->
      <svg class="concept-svg" ref="conceptSvg" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice">
        <defs>
          <!-- 思考区渐变 - 紫蓝色 -->
          <linearGradient id="thinkingGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" class="thinking-stop-1" />
            <stop offset="100%" class="thinking-stop-2" />
          </linearGradient>

          <!-- 行动区渐变 - 青蓝色 -->
          <linearGradient id="actionGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" class="action-stop-1" />
            <stop offset="100%" class="action-stop-2" />
          </linearGradient>

          <!-- MCP通道渐变 -->
          <linearGradient id="mcpChannelGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" class="mcp-channel-start" />
            <stop offset="50%" class="mcp-channel-mid" />
            <stop offset="100%" class="mcp-channel-end" />
          </linearGradient>

          <!-- 发光滤镜 -->
          <filter id="softGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="0.3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <!-- 强发光滤镜 -->
          <filter id="strongGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="0.5" result="blur" />
            <feComposite in="blur" operator="over" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <!-- 背景网格 -->
        <pattern id="grid" width="4" height="4" patternUnits="userSpaceOnUse">
          <path d="M 4 0 L 0 0 0 4" fill="none" class="grid-line" />
        </pattern>
        <rect width="100" height="100" fill="url(#grid)" class="grid-rect" />

        <!-- ===== 左侧：思考区 ===== -->
        <g class="thinking-zone">
          <!-- 大脑轮廓/神经网络节点 -->
          <g class="neural-nodes">
            <circle v-for="(node, i) in thinkingNodes" :key="'tn'+i"
              :cx="node.x" :cy="node.y" :r="node.r"
              fill="url(#thinkingGradient)"
              class="thinking-node"
              :style="{ animationDelay: node.delay + 's' }" />
          </g>

          <!-- 神经连接线 -->
          <g class="neural-connections">
            <line v-for="(conn, i) in neuralConnections" :key="'nc'+i"
              :x1="conn.x1" :y1="conn.y1" :x2="conn.x2" :y2="conn.y2"
              stroke="url(#thinkingGradient)"
              class="neural-line"
              :style="{ animationDelay: conn.delay + 's' }" />
          </g>

          <!-- 漂浮的文字符号 -->
          <text v-for="(text, i) in floatingTexts" :key="'ft'+i"
            :x="text.x" :y="text.y"
            class="floating-text"
            :style="{ animationDelay: text.delay + 's', fontSize: text.size }">
            {{ text.char }}
          </text>

          <!-- 对话气泡 -->
          <g v-for="(bubble, i) in thoughtBubbles" :key="'tb'+i"
            class="thought-bubble"
            :style="{ animationDelay: bubble.delay + 's' }">
            <ellipse :cx="bubble.x" :cy="bubble.y" :rx="bubble.rx" :ry="bubble.ry"
              class="bubble-ellipse" />
            <circle :cx="bubble.x - bubble.rx * 0.6" :cy="bubble.y + bubble.ry * 0.8" r="0.4" class="bubble-dot" />
            <circle :cx="bubble.x - bubble.rx * 0.8" :cy="bubble.y + bubble.ry * 1.1" r="0.25" class="bubble-dot" />
          </g>
        </g>

        <!-- ===== 中间：MCP转换通道 ===== -->
        <g class="mcp-channel-zone">
          <!-- 主通道 -->
          <path d="M 42 10 Q 50 50 58 10 M 42 90 Q 50 50 58 90"
            class="channel-path" fill="none" stroke="url(#mcpChannelGradient)" />

          <!-- 能量流动粒子 -->
          <circle v-for="(particle, i) in energyParticles" :key="'ep'+i"
            :cx="particle.x" :cy="particle.y" r="0.3"
            class="energy-particle"
            :style="{ animationDelay: particle.delay + 's' }">
            <animate attributeName="cx"
              :values="particle.pathX"
              dur="3s" repeatCount="indefinite" />
            <animate attributeName="cy"
              :values="particle.pathY"
              dur="3s" repeatCount="indefinite" />
            <animate attributeName="opacity"
              values="0;1;1;0" dur="3s" repeatCount="indefinite" />
          </circle>

          <!-- 转换节点 -->
          <g class="transform-nodes">
            <circle cx="50" cy="30" r="1.5" class="transform-node" />
            <circle cx="50" cy="50" r="2" class="transform-node central" />
            <circle cx="50" cy="70" r="1.5" class="transform-node" />
          </g>

          <!-- MCP标签 -->
          <text x="50" y="50" class="mcp-label" text-anchor="middle" dominant-baseline="middle">MCP</text>
        </g>

        <!-- ===== 右侧：行动区 ===== -->
        <g class="action-zone">
          <!-- 工具/模块图标 -->
          <g v-for="(tool, i) in toolIcons" :key="'tool'+i"
            class="tool-icon"
            :transform="'translate(' + tool.x + ',' + tool.y + ')'"
            :style="{ animationDelay: tool.delay + 's' }">
            <!-- 工具背景框 -->
            <rect x="-1.5" y="-1.5" width="3" height="3" rx="0.5" class="tool-bg" />
            <!-- 工具图标 -->
            <path :d="tool.path" class="tool-symbol" />
          </g>

          <!-- 执行箭头/流程线 -->
          <g class="action-arrows">
            <path v-for="(arrow, i) in actionArrows" :key="'aa'+i"
              :d="arrow.path"
              class="action-arrow"
              :style="{ animationDelay: arrow.delay + 's' }" />
          </g>

          <!-- 成果/输出块 -->
          <rect v-for="(block, i) in outputBlocks" :key="'ob'+i"
            :x="block.x" :y="block.y" :width="block.w" :height="block.h"
            rx="0.3" class="output-block"
            :style="{ animationDelay: block.delay + 's' }" />

          <!-- 机械臂/执行器 -->
          <g class="actuator" style="animationDelay: 1s">
            <path d="M 75 60 L 80 55 L 85 60 L 80 65 Z" class="actuator-head" />
            <line x1="80" y1="55" x2="80" y2="45" class="actuator-arm" />
            <circle cx="80" cy="45" r="1" class="actuator-joint" />
          </g>
        </g>
      </svg>

      <!-- 流动光效 -->
      <div class="flowing-orb orb-1"></div>
      <div class="flowing-orb orb-2"></div>
      <div class="flowing-orb orb-3"></div>
    </div>

    <!-- 登录卡片 -->
    <div class="login-card" :class="{ 'card-visible': isReady }">
      <!-- 卡片边框光效 -->
      <div class="card-glow"></div>

      <div class="login-header">
        <!-- Logo -->
        <div class="logo-container">
          <div class="logo-brain">
            <svg viewBox="0 0 40 40" class="brain-svg">
              <!-- 大脑左侧（思考） -->
              <path d="M10 20 Q8 15 12 12 Q16 9 18 12 Q20 14 18 18 Q16 22 12 22 Q10 22 10 20"
                class="brain-left" />
              <!-- 转换节点 -->
              <circle cx="20" cy="20" r="3" class="brain-core" />
              <!-- 大脑右侧（行动） -->
              <path d="M30 20 Q32 15 28 12 Q24 9 22 12 Q20 14 22 18 Q24 22 28 22 Q30 22 30 20"
                class="brain-right" />
              <!-- 连接线 -->
              <line x1="17" y1="20" x2="17" y2="20" class="brain-connector" />
            </svg>
          </div>
          <div class="logo-rings">
            <div class="logo-ring ring-1"></div>
            <div class="logo-ring ring-2"></div>
          </div>
        </div>

        <h1 class="login-title">
          <span class="title-text">MCP</span>
          <span class="title-accent">HUB</span>
        </h1>
        <p class="login-subtitle">{{ t('login_subtitle') }}</p>
        <p class="login-concept">{{ t('login_concept') }}</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" class="login-form">
        <el-form-item prop="username">
          <div class="input-wrapper">
            <div class="input-icon">
              <el-icon><User /></el-icon>
            </div>
            <el-input
              v-model="form.username"
              :placeholder="t('login_username')"
              size="large"
              class="custom-input"
              @focus="activeField = 'username'"
              @blur="activeField = ''"
            />
            <div class="input-line" :class="{ active: activeField === 'username' }"></div>
          </div>
        </el-form-item>

        <el-form-item prop="password">
          <div class="input-wrapper">
            <div class="input-icon">
              <el-icon><Lock /></el-icon>
            </div>
            <el-input
              v-model="form.password"
              type="password"
              :placeholder="t('login_password')"
              size="large"
              show-password
              class="custom-input"
              @focus="activeField = 'password'"
              @blur="activeField = ''"
              @keyup.enter="handleLogin"
            />
            <div class="input-line" :class="{ active: activeField === 'password' }"></div>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-btn"
            @click="handleLogin"
          >
            <span class="btn-content">
              <span class="btn-text">{{ t('login_button') }}</span>
              <span class="btn-icon">
                <svg viewBox="0 0 24 24" fill="none">
                  <path d="M5 12H19M19 12L12 5M19 12L12 19" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
            </span>
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 底部装饰 -->
      <div class="card-footer">
        <div class="tech-line"></div>
        <span class="footer-text">DESIGN BY AI</span>
        <div class="tech-line"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { login } from '../api/auth'
import { useI18n } from '../i18n.js'

const { t } = useI18n()
const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const activeField = ref('')
const isReady = ref(false)

const form = ref({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: t('login_username_required'), trigger: 'blur' }
  ],
  password: [
    { required: true, message: t('login_password_required'), trigger: 'blur' }
  ]
}

// 思考区数据
const thinkingNodes = [
  { x: 10, y: 20, r: 0.8, delay: 0 },
  { x: 15, y: 35, r: 1, delay: 0.3 },
  { x: 8, y: 50, r: 0.6, delay: 0.6 },
  { x: 20, y: 45, r: 0.9, delay: 0.9 },
  { x: 12, y: 65, r: 0.7, delay: 1.2 },
  { x: 25, y: 30, r: 0.5, delay: 1.5 },
  { x: 18, y: 55, r: 0.8, delay: 1.8 },
  { x: 5, y: 40, r: 0.6, delay: 2.1 },
  { x: 22, y: 70, r: 0.7, delay: 2.4 },
]

const neuralConnections = [
  { x1: 10, y1: 20, x2: 15, y2: 35, delay: 0 },
  { x1: 15, y1: 35, x2: 20, y2: 45, delay: 0.2 },
  { x1: 8, y1: 50, x2: 18, y2: 55, delay: 0.4 },
  { x1: 20, y1: 45, x2: 25, y2: 30, delay: 0.6 },
  { x1: 12, y1: 65, x2: 22, y2: 70, delay: 0.8 },
  { x1: 5, y1: 40, x2: 8, y2: 50, delay: 1.0 },
]

const floatingTexts = [
  { x: 6, y: 25, char: '?', size: '2px', delay: 0 },
  { x: 22, y: 22, char: '{ }', size: '1.5px', delay: 0.5 },
  { x: 14, y: 80, char: '...', size: '2px', delay: 1 },
  { x: 3, y: 60, char: '"', size: '2.5px', delay: 1.5 },
  { x: 28, y: 50, char: '( )', size: '1.5px', delay: 2 },
]

const thoughtBubbles = [
  { x: 8, y: 30, rx: 3, ry: 2, delay: 0 },
  { x: 20, y: 60, rx: 2.5, ry: 1.8, delay: 1 },
]

// MCP通道数据
const energyParticles = [
  { x: 35, y: 50, pathX: '35;50;65', pathY: '30;50;70', delay: 0 },
  { x: 35, y: 50, pathX: '35;50;65', pathY: '70;50;30', delay: 1 },
  { x: 35, y: 50, pathX: '35;50;65', pathY: '50;50;50', delay: 2 },
]

// 行动区数据
const toolIcons = [
  { x: 75, y: 20, path: 'M-0.8,-0.8 L0.8,-0.8 L0.8,0.8 L-0.8,0.8 Z', delay: 0 },
  { x: 85, y: 35, path: 'M0,-1 L0.8,0 L0,1 L-0.8,0 Z', delay: 0.3 },
  { x: 80, y: 75, path: 'M-0.6,-0.6 L0.6,-0.6 L0,0.6 Z', delay: 0.6 },
  { x: 70, y: 40, path: 'M-0.5,-0.8 L0.5,-0.8 L0.5,0.8 L-0.5,0.8 Z', delay: 0.9 },
  { x: 90, y: 55, path: 'M0,-0.7 L0.7,0 L0,0.7 L-0.7,0 Z', delay: 1.2 },
]

const actionArrows = [
  { path: 'M 72 25 Q 78 28 82 25', delay: 0 },
  { path: 'M 78 42 Q 84 45 88 42', delay: 0.5 },
  { path: 'M 72 70 Q 78 68 82 70', delay: 1 },
]

const outputBlocks = [
  { x: 88, y: 18, w: 5, h: 4, delay: 0 },
  { x: 82, y: 62, w: 6, h: 3, delay: 0.7 },
  { x: 75, y: 80, w: 4, h: 5, delay: 1.4 },
]

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await login(form.value.username, form.value.password)
    if (res.access_token) {
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('user', JSON.stringify(res.user))
      ElMessage.success(t('login_success'))
      router.push('/')
    }
  } catch (error) {
    const detail = error.response?.data?.detail || t('login_failed')
    ElMessage.error(detail)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  setTimeout(() => {
    isReady.value = true
  }, 100)
})
</script>

<style scoped>
/* ===== 容器与背景 ===== */
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: var(--login-bg);
  transition: background 0.5s ease;
}

.bg-layer {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

/* ===== 主视觉SVG ===== */
.concept-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0.6;
}

html.dark .concept-svg {
  opacity: 0.8;
}

/* 网格 */
.grid-rect {
  opacity: 0.3;
}

html:not(.dark) .grid-rect {
  opacity: 0.15;
}

.grid-line {
  stroke: var(--mcp-connection-color);
  stroke-width: 0.1;
}

/* 渐变颜色 - 亮色主题 */
.thinking-stop-1 { stop-color: #8b5cf6; }
.thinking-stop-2 { stop-color: #6366f1; }
.action-stop-1 { stop-color: #06b6d4; }
.action-stop-2 { stop-color: #0ea5e9; }
.mcp-channel-start { stop-color: #8b5cf6; }
.mcp-channel-mid { stop-color: #06b6d4; }
.mcp-channel-end { stop-color: #10b981; }

/* 渐变颜色 - 暗色主题 */
html.dark .thinking-stop-1 { stop-color: #a78bfa; }
html.dark .thinking-stop-2 { stop-color: #818cf8; }
html.dark .action-stop-1 { stop-color: #22d3ee; }
html.dark .action-stop-2 { stop-color: #38bdf8; }
html.dark .mcp-channel-start { stop-color: #a78bfa; }
html.dark .mcp-channel-mid { stop-color: #22d3ee; }
html.dark .mcp-channel-end { stop-color: #34d399; }

/* ===== 思考区样式 ===== */
.thinking-node {
  filter: url(#softGlow);
  animation: nodeFloat 4s ease-in-out infinite;
}

@keyframes nodeFloat {
  0%, 100% { transform: translateY(0); opacity: 0.7; }
  50% { transform: translateY(-1); opacity: 1; }
}

.neural-line {
  stroke-width: 0.15;
  opacity: 0.5;
  animation: linePulse 3s ease-in-out infinite;
}

@keyframes linePulse {
  0%, 100% { opacity: 0.3; stroke-width: 0.1; }
  50% { opacity: 0.8; stroke-width: 0.2; }
}

.floating-text {
  fill: var(--mcp-node-color);
  font-family: 'JetBrains Mono', monospace;
  opacity: 0.6;
  animation: textFloat 6s ease-in-out infinite;
}

html.dark .floating-text {
  filter: url(#softGlow);
}

@keyframes textFloat {
  0%, 100% { opacity: 0.4; transform: translateY(0); }
  50% { opacity: 0.8; transform: translateY(-1); }
}

.thought-bubble {
  animation: bubbleFloat 5s ease-in-out infinite;
}

.bubble-ellipse {
  fill: none;
  stroke: var(--mcp-connection-color);
  stroke-width: 0.2;
  stroke-dasharray: 1;
  animation: bubbleDash 10s linear infinite;
}

.bubble-dot {
  fill: var(--mcp-node-color);
  opacity: 0.5;
}

@keyframes bubbleFloat {
  0%, 100% { opacity: 0.5; transform: translateY(0); }
  50% { opacity: 0.8; transform: translateY(-0.5); }
}

@keyframes bubbleDash {
  to { stroke-dashoffset: -10; }
}

/* ===== MCP通道样式 ===== */
.channel-path {
  stroke-width: 0.3;
  stroke-dasharray: 2 1;
  animation: channelFlow 3s linear infinite;
  filter: url(#softGlow);
}

@keyframes channelFlow {
  to { stroke-dashoffset: -6; }
}

.energy-particle {
  fill: var(--mcp-node-color);
  filter: url(#strongGlow);
}

.transform-node {
  fill: none;
  stroke: var(--mcp-node-color);
  stroke-width: 0.2;
  animation: nodeRotate 4s linear infinite;
}

.transform-node.central {
  stroke-width: 0.3;
  filter: url(#strongGlow);
}

@keyframes nodeRotate {
  from { transform-origin: center; }
  to { transform: rotate(360deg); }
}

.mcp-label {
  fill: var(--text-subtle);
  font-size: 1.5px;
  font-weight: 600;
  letter-spacing: 0.5;
  opacity: 0.6;
}

/* ===== 行动区样式 ===== */
.tool-icon {
  animation: toolAppear 4s ease-in-out infinite;
}

.tool-bg {
  fill: var(--bg-card);
  stroke: var(--mcp-node-color);
  stroke-width: 0.15;
  opacity: 0.8;
}

.tool-symbol {
  fill: var(--mcp-node-color);
  opacity: 0.8;
}

@keyframes toolAppear {
  0%, 100% { opacity: 0.5; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.1); }
}

.action-arrow {
  fill: none;
  stroke: var(--mcp-node-color);
  stroke-width: 0.2;
  stroke-linecap: round;
  stroke-dasharray: 2;
  animation: arrowFlow 2s linear infinite;
}

@keyframes arrowFlow {
  to { stroke-dashoffset: -4; }
}

.output-block {
  fill: none;
  stroke: var(--mcp-node-color);
  stroke-width: 0.15;
  rx: 0.3;
  animation: blockPulse 3s ease-in-out infinite;
}

@keyframes blockPulse {
  0%, 100% { opacity: 0.4; stroke-width: 0.1; }
  50% { opacity: 0.9; stroke-width: 0.2; }
}

.actuator {
  animation: actuatorMove 5s ease-in-out infinite;
}

.actuator-head {
  fill: var(--mcp-node-color);
  opacity: 0.8;
}

.actuator-arm {
  stroke: var(--mcp-node-color);
  stroke-width: 0.3;
}

.actuator-joint {
  fill: var(--mcp-node-color);
}

@keyframes actuatorMove {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(2); }
  75% { transform: translateX(-2); }
}

/* ===== 流动光球 ===== */
.flowing-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.3;
  animation: orbFloat 15s ease-in-out infinite;
}

html.dark .flowing-orb {
  opacity: 0.4;
}

.orb-1 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, var(--mcp-gradient-start) 0%, transparent 70%);
  top: -5%;
  left: 10%;
  animation-delay: 0s;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, var(--mcp-gradient-end) 0%, transparent 70%);
  bottom: -10%;
  right: 5%;
  animation-delay: -5s;
}

.orb-3 {
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, #10b981 0%, transparent 70%);
  top: 50%;
  left: 45%;
  animation-delay: -10s;
}

@keyframes orbFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -20px) scale(1.1); }
  66% { transform: translate(-20px, 30px) scale(0.9); }
}

/* ===== 登录卡片 ===== */
.login-card {
  width: 100%;
  max-width: 420px;
  position: relative;
  z-index: 10;
  background: var(--login-card-bg);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 48px 40px;
  border: 1px solid var(--login-card-border);
  box-shadow: var(--login-card-shadow);
  opacity: 0;
  transform: translateY(30px) scale(0.95);
  transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

.card-visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.card-glow {
  position: absolute;
  inset: -2px;
  border-radius: 22px;
  background: var(--accent-gradient);
  background-size: 200% 200%;
  animation: borderGlow 4s ease infinite;
  z-index: -1;
  opacity: 0.3;
}

html.dark .card-glow {
  opacity: 0.5;
}

@keyframes borderGlow {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

/* ===== Logo ===== */
.logo-container {
  position: relative;
  width: 70px;
  height: 70px;
  margin: 0 auto 20px;
}

.logo-brain {
  width: 50px;
  height: 50px;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
}

.brain-svg {
  width: 100%;
  height: 100%;
}

.brain-left {
  fill: none;
  stroke: #8b5cf6;
  stroke-width: 1.5;
  opacity: 0.8;
  animation: brainPulse 2s ease-in-out infinite;
}

html.dark .brain-left {
  stroke: #a78bfa;
  filter: drop-shadow(0 0 3px rgba(167, 139, 250, 0.5));
}

.brain-right {
  fill: none;
  stroke: #06b6d4;
  stroke-width: 1.5;
  opacity: 0.8;
  animation: brainPulse 2s ease-in-out infinite 0.5s;
}

html.dark .brain-right {
  stroke: #22d3ee;
  filter: drop-shadow(0 0 3px rgba(34, 211, 238, 0.5));
}

.brain-core {
  fill: none;
  stroke: var(--accent-color);
  stroke-width: 1;
  animation: coreRotate 4s linear infinite;
}

@keyframes brainPulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

@keyframes coreRotate {
  from { transform: rotate(0deg); transform-origin: 20px 20px; }
  to { transform: rotate(360deg); transform-origin: 20px 20px; }
}

.logo-rings {
  position: absolute;
  inset: 0;
}

.logo-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid;
  animation: ringPulse 3s ease-in-out infinite;
}

.ring-1 {
  inset: 0;
  border-color: var(--mcp-connection-color);
}

.ring-2 {
  inset: -8px;
  border-color: var(--mcp-connection-color);
  animation-delay: 0.5s;
}

@keyframes ringPulse {
  0%, 100% { transform: scale(1); opacity: 0.5; }
  50% { transform: scale(1.1); opacity: 0.8; }
}

/* ===== 标题 ===== */
.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-title {
  font-size: 32px;
  font-weight: 800;
  margin: 0;
  letter-spacing: 4px;
}

.title-text {
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.title-accent {
  color: var(--accent-color);
  text-shadow: var(--accent-shadow);
  margin-left: 8px;
}

.login-subtitle {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 12px 0 0;
}

.login-concept {
  color: var(--text-muted);
  font-size: 12px;
  margin: 8px 0 0;
  opacity: 0.8;
}

/* ===== 表单 ===== */
.login-form {
  margin-top: 28px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 24px;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
}

.input-icon {
  position: absolute;
  left: 16px;
  z-index: 2;
  color: var(--text-muted);
  transition: all 0.3s ease;
}

.input-wrapper:focus-within .input-icon {
  color: var(--accent-color);
}

.login-form :deep(.el-input__wrapper) {
  background: var(--login-input-bg) !important;
  box-shadow: none !important;
  border: 1px solid var(--login-input-border);
  border-radius: 12px;
  padding: 4px 16px 4px 44px;
  transition: all 0.3s ease;
}

.login-form :deep(.el-input__wrapper:hover) {
  border-color: var(--mcp-connection-color);
}

.login-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 2px var(--mcp-glow-color) !important;
}

.login-form :deep(.el-input__inner) {
  color: var(--text-primary) !important;
  height: 44px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 15px;
  letter-spacing: 0.3px;
}

.login-form :deep(.el-input__inner::placeholder) {
  color: var(--text-placeholder);
}

.input-line {
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 2px;
  background: var(--accent-gradient);
  transition: all 0.3s ease;
  transform: translateX(-50%);
  border-radius: 2px;
}

.input-line.active {
  width: 80%;
}

/* ===== 登录按钮 ===== */
.login-btn {
  width: 100%;
  height: 50px;
  font-size: 16px;
  font-weight: 600;
  background: var(--accent-gradient) !important;
  border: none !important;
  border-radius: 12px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
  box-shadow: var(--accent-shadow);
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px var(--mcp-glow-color);
}

.btn-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-icon svg {
  width: 18px;
  height: 18px;
  transition: transform 0.3s ease;
}

.login-btn:hover .btn-icon svg {
  transform: translateX(4px);
}

/* ===== 底部 ===== */
.card-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 28px;
}

.tech-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--mcp-connection-color), transparent);
}

.footer-text {
  font-size: 11px;
  color: var(--text-subtle);
  letter-spacing: 2px;
  text-transform: uppercase;
}

/* ===== 响应式 ===== */
@media (max-width: 480px) {
  .login-card {
    margin: 16px;
    padding: 32px 24px;
  }

  .login-title {
    font-size: 26px;
  }
}
</style>