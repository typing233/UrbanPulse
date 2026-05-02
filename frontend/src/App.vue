<template>
  <div class="app-container">
    <header class="app-header">
      <h1 class="app-title">🌆 UrbanPulse</h1>
      <p class="app-subtitle">城市健康状况实时监控系统</p>
      <div class="header-controls">
        <select v-model="selectedCity" class="city-selector">
          <option value="北京">北京</option>
          <option value="上海">上海</option>
        </select>
        <button @click="openLLMConfig" class="config-btn">
          ⚙️ LLM 配置
        </button>
      </div>
    </header>

    <main class="main-content">
      <div class="view-tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.id"
          @click="activeView = tab.id"
          :class="['tab-btn', { active: activeView === tab.id }]"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="view-container">
        <City3DView 
          v-if="activeView === '3d'"
          :city="selectedCity"
          @anomaly="handleAnomaly"
        />
        
        <TimelineView 
          v-else-if="activeView === 'timeline'"
          :city="selectedCity"
        />
        
        <div v-else class="data-view">
          <h2>数据概览</h2>
          <div class="metrics-grid">
            <div class="metric-card">
              <div class="metric-label">🚗 交通拥堵指数</div>
              <div class="metric-value" :class="getTrafficClass(currentData?.traffic_index)">
                {{ currentData?.traffic_index || '--' }}
              </div>
              <div class="metric-status">{{ currentData?.traffic_level || '加载中' }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">🌬️ 空气质量 AQI</div>
              <div class="metric-value" :class="getAQIClass(currentData?.aqi)">
                {{ currentData?.aqi || '--' }}
              </div>
              <div class="metric-status">{{ currentData?.aqi_level?.[0] || '加载中' }}</div>
            </div>
          </div>
          <div class="timestamp">
            最后更新: {{ lastUpdateTime }}
          </div>
        </div>
      </div>
    </main>

    <LLMConfigModal 
      v-if="showLLMConfig"
      :config="llmConfig"
      @close="showLLMConfig = false"
      @save="saveLLMConfig"
      @test="testLLMConnection"
    />

    <div v-if="anomalies.length > 0" class="anomaly-alerts">
      <div 
        v-for="(anomaly, index) in anomalies" 
        :key="index"
        class="alert-item"
        :class="anomaly.severity"
      >
        <span class="alert-icon">⚠️</span>
        <span class="alert-text">{{ anomaly.message }}</span>
        <button @click="dismissAlert(index)" class="alert-close">×</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import City3DView from './components/City3DView.vue'
import TimelineView from './components/TimelineView.vue'
import LLMConfigModal from './components/LLMConfigModal.vue'
import { dataService } from './utils/dataService'

const selectedCity = ref('北京')
const activeView = ref('3d')
const showLLMConfig = ref(false)
const currentData = ref(null)
const lastUpdateTime = ref('--')
const anomalies = ref([])

const tabs = [
  { id: '3d', label: '🏙️ 3D 城市视图' },
  { id: 'timeline', label: '📊 24小时时间轴' },
  { id: 'data', label: '📈 数据概览' }
]

const llmConfig = reactive({
  baseUrl: '',
  apiKey: '',
  modelName: 'gpt-3.5-turbo',
  enabled: false
})

let dataUpdateInterval = null

const getTrafficClass = (value) => {
  if (!value) return ''
  if (value < 50) return 'good'
  if (value < 70) return 'moderate'
  return 'bad'
}

const getAQIClass = (value) => {
  if (!value) return ''
  if (value <= 50) return 'aqi-good'
  if (value <= 100) return 'aqi-moderate'
  if (value <= 150) return 'aqi-bad'
  return 'aqi-severe'
}

const openLLMConfig = () => {
  showLLMConfig.value = true
}

const saveLLMConfig = (config) => {
  Object.assign(llmConfig, config)
}

const testLLMConnection = async (config) => {
  try {
    const result = await dataService.testLLMConnection(config)
    return result
  } catch (error) {
    return false
  }
}

const loadCurrentData = async () => {
  try {
    const data = await dataService.getCurrentData(selectedCity.value)
    currentData.value = data
    lastUpdateTime.value = new Date().toLocaleTimeString('zh-CN')
  } catch (error) {
    console.error('加载数据失败:', error)
  }
}

const handleAnomaly = (anomaly) => {
  anomalies.value.push({
    ...anomaly,
    timestamp: Date.now()
  })
  
  setTimeout(() => {
    const index = anomalies.value.findIndex(a => a.timestamp === anomaly.timestamp)
    if (index > -1) {
      anomalies.value.splice(index, 1)
    }
  }, 10000)
}

const dismissAlert = (index) => {
  anomalies.value.splice(index, 1)
}

onMounted(() => {
  loadCurrentData()
  dataUpdateInterval = setInterval(loadCurrentData, 5000)
})

onUnmounted(() => {
  if (dataUpdateInterval) {
    clearInterval(dataUpdateInterval)
  }
})
</script>

<style scoped>
.app-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(15, 12, 41, 0.9);
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 30px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.app-title {
  font-size: 1.8rem;
  font-weight: bold;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
}

.app-subtitle {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.9rem;
  margin: 0;
}

.header-controls {
  display: flex;
  gap: 15px;
  align-items: center;
}

.city-selector {
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-size: 0.95rem;
  cursor: pointer;
}

.city-selector option {
  background: #1a1a2e;
  color: white;
}

.config-btn {
  padding: 8px 16px;
  border-radius: 8px;
  border: none;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.config-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.view-tabs {
  display: flex;
  gap: 10px;
  padding: 15px 30px;
  background: rgba(0, 0, 0, 0.2);
}

.tab-btn {
  padding: 10px 20px;
  border-radius: 25px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.tab-btn.active {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}

.view-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.data-view {
  padding: 30px;
  color: white;
}

.data-view h2 {
  margin-bottom: 30px;
  font-size: 1.5rem;
  color: rgba(255, 255, 255, 0.9);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 30px;
  margin-bottom: 30px;
}

.metric-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 30px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.metric-label {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 15px;
}

.metric-value {
  font-size: 3rem;
  font-weight: bold;
  margin-bottom: 10px;
}

.metric-value.good { color: #00c853; }
.metric-value.moderate { color: #ffab00; }
.metric-value.bad { color: #ff3d00; }
.metric-value.aqi-good { color: #00e400; }
.metric-value.aqi-moderate { color: #ffff00; }
.metric-value.aqi-bad { color: #ff7e00; }
.metric-value.aqi-severe { color: #ff0000; }

.metric-status {
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.5);
}

.timestamp {
  text-align: right;
  color: rgba(255, 255, 255, 0.4);
  font-size: 0.85rem;
}

.anomaly-alerts {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 15px 20px;
  border-radius: 10px;
  background: rgba(255, 61, 0, 0.9);
  color: white;
  min-width: 300px;
  animation: slideIn 0.3s ease;
}

.alert-item.warning {
  background: rgba(255, 171, 0, 0.9);
}

.alert-item.error {
  background: rgba(255, 61, 0, 0.9);
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.alert-icon {
  font-size: 1.2rem;
}

.alert-text {
  flex: 1;
  font-size: 0.95rem;
}

.alert-close {
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.3s;
}

.alert-close:hover {
  opacity: 1;
}
</style>
