<template>
  <div class="timeline-container">
    <div class="timeline-header">
      <h2>{{ city }} - 24小时数据演变</h2>
      <div class="time-indicator">
        当前时间: <span class="highlight">{{ currentTime }}</span>
        <span class="time-marker" :style="{ left: timeMarkerPosition + '%' }"></span>
      </div>
    </div>

    <div class="scrollytelling-container" ref="scrollContainer">
      <div class="canvas-wrapper">
        <canvas ref="particleCanvas" class="particle-canvas"></canvas>
        <div class="canvas-overlay">
          <div class="current-hour-label">
            {{ Math.floor(currentHour) }}:00
          </div>
        </div>
      </div>

      <div class="scroll-steps">
        <div 
          v-for="(step, index) in steps" 
          :key="index"
          class="step-section"
          :class="{ active: activeStep === index }"
          :style="{ transform: `translateY(${(index - activeStep) * 50}px)`, opacity: activeStep === index ? 1 : 0.5 }"
        >
          <div class="step-content">
            <h3>{{ step.title }}</h3>
            <p>{{ step.description }}</p>
            <div class="step-metrics" v-if="step.hourData">
              <div class="step-metric">
                <span class="metric-name">交通拥堵</span>
                <span class="metric-value" :class="getTrafficClass(step.hourData.traffic_index)">
                  {{ step.hourData.traffic_index?.toFixed(1) || '--' }}
                </span>
              </div>
              <div class="step-metric">
                <span class="metric-name">空气质量</span>
                <span class="metric-value" :class="getAQIClass(step.hourData.aqi)">
                  {{ step.hourData.aqi?.toFixed(0) || '--' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="timeline-controls">
      <div class="time-slider-container">
        <input 
          type="range" 
          min="0" 
          max="24" 
          step="0.5"
          v-model="currentHour"
          class="time-slider"
        />
        <div class="slider-labels">
          <span>00:00</span>
          <span>06:00</span>
          <span>12:00</span>
          <span>18:00</span>
          <span>24:00</span>
        </div>
      </div>
      <div class="play-controls">
        <button @click="togglePlay" class="play-btn">
          {{ isPlaying ? '⏸️ 暂停' : '▶️ 播放' }}
        </button>
        <button @click="resetTimeline" class="reset-btn">
          🔄 重置
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { dataService } from '../utils/dataService'

const props = defineProps({
  city: {
    type: String,
    default: '北京'
  }
})

const particleCanvas = ref(null)
const scrollContainer = ref(null)

const hourlyData = ref([])
const currentHour = ref(0)
const isPlaying = ref(false)
const activeStep = ref(0)

let animationFrameId = null
let playInterval = null
let canvasContext = null
let particleSystem = null

const steps = computed(() => {
  const baseSteps = [
    { title: '🌙 午夜时分', description: '城市逐渐沉睡，交通流量达到最低点', hour: 0 },
    { title: '🌅 黎明前的寂静', description: '极少数的早起者开始活动，城市即将苏醒', hour: 4 },
    { title: '🚗 早高峰开始', description: '上班族开始出行，交通压力逐渐增大', hour: 7 },
    { title: '🌆 早高峰顶峰', description: '交通拥堵达到全天第一个高峰，建议错峰出行', hour: 9 },
    { title: '💼 工作时段', description: '交通流量有所缓解，城市进入正常运转', hour: 12 },
    { title: '🌇 晚高峰前夕', description: '下班时间临近，交通压力开始回升', hour: 16 },
    { title: '🚦 晚高峰顶峰', description: '全天最拥堵的时段，建议使用公共交通', hour: 18 },
    { title: '✨ 夜间生活', description: '交通逐渐缓解，城市灯光璀璨', hour: 21 },
    { title: '🌙 深夜回归', description: '城市再次进入宁静，为新的一天做准备', hour: 23 }
  ]

  return baseSteps.map(step => {
    const hourData = hourlyData.value.find(d => Math.floor(d.hour) === step.hour)
    return {
      ...step,
      hourData
    }
  })
})

const currentTime = computed(() => {
  const hour = Math.floor(currentHour.value)
  const minute = Math.floor((currentHour.value % 1) * 60)
  return `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`
})

const timeMarkerPosition = computed(() => {
  return (currentHour.value / 24) * 100
})

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

const getColorForValue = (value, type = 'traffic') => {
  if (type === 'traffic') {
    if (value < 30) return { r: 0, g: 200, b: 83 }
    if (value < 50) return { r: 100, g: 221, b: 23 }
    if (value < 70) return { r: 255, g: 171, b: 0 }
    if (value < 90) return { r: 255, g: 109, b: 0 }
    return { r: 255, g: 61, b: 0 }
  } else {
    if (value <= 50) return { r: 0, g: 228, b: 0 }
    if (value <= 100) return { r: 255, g: 255, b: 0 }
    if (value <= 150) return { r: 255, g: 126, b: 0 }
    if (value <= 200) return { r: 255, g: 0, b: 0 }
    if (value <= 300) return { r: 153, g: 0, b: 76 }
    return { r: 126, g: 0, b: 35 }
  }
}

class Particle {
  constructor(x, y, canvasWidth, canvasHeight) {
    this.x = x
    this.y = y
    this.vx = (Math.random() - 0.5) * 2
    this.vy = (Math.random() - 0.5) * 2
    this.radius = Math.random() * 3 + 1
    this.baseRadius = this.radius
    this.canvasWidth = canvasWidth
    this.canvasHeight = canvasHeight
    this.trafficValue = 50
    this.aqiValue = 50
    this.alpha = 0.5 + Math.random() * 0.5
    this.baseAlpha = this.alpha
  }

  update(hourProgress, trafficValue, aqiValue) {
    this.trafficValue = trafficValue
    this.aqiValue = aqiValue

    const speedFactor = 0.3 + (trafficValue / 100) * 1.5
    this.x += this.vx * speedFactor
    this.y += this.vy * speedFactor

    if (this.x < 0) this.x = this.canvasWidth
    if (this.x > this.canvasWidth) this.x = 0
    if (this.y < 0) this.y = this.canvasHeight
    if (this.y > this.canvasHeight) this.y = 0

    const pulseFactor = 0.5 + Math.sin(Date.now() * 0.003 + this.x * 0.1) * 0.5
    this.radius = this.baseRadius * (1 + (trafficValue / 100) * 0.5 * pulseFactor)
    this.alpha = this.baseAlpha * (0.5 + (aqiValue / 200) * 0.5)
  }

  draw(ctx, hourProgress) {
    const trafficColor = getColorForValue(this.trafficValue, 'traffic')
    const aqiColor = getColorForValue(this.aqiValue, 'aqi')

    const r = Math.floor(trafficColor.r * (1 - hourProgress) + aqiColor.r * hourProgress)
    const g = Math.floor(trafficColor.g * (1 - hourProgress) + aqiColor.g * hourProgress)
    const b = Math.floor(trafficColor.b * (1 - hourProgress) + aqiColor.b * hourProgress)

    ctx.beginPath()
    ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${this.alpha})`
    ctx.fill()

    ctx.beginPath()
    ctx.arc(this.x, this.y, this.radius * 1.5, 0, Math.PI * 2)
    const gradient = ctx.createRadialGradient(
      this.x, this.y, 0,
      this.x, this.y, this.radius * 1.5
    )
    gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${this.alpha * 0.5})`)
    gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`)
    ctx.fillStyle = gradient
    ctx.fill()
  }
}

const initCanvas = () => {
  if (!particleCanvas.value) return

  const canvas = particleCanvas.value
  const container = canvas.parentElement

  canvas.width = container.clientWidth
  canvas.height = container.clientHeight

  canvasContext = canvas.getContext('2d')

  particleSystem = {
    particles: [],
    width: canvas.width,
    height: canvas.height
  }

  const particleCount = 200
  for (let i = 0; i < particleCount; i++) {
    const x = Math.random() * canvas.width
    const y = Math.random() * canvas.height
    particleSystem.particles.push(new Particle(x, y, canvas.width, canvas.height))
  }
}

const drawFluidEffect = (ctx, hourProgress, trafficValue, aqiValue) => {
  if (!particleSystem) return

  const gradient = ctx.createLinearGradient(
    0, 0, 
    particleSystem.width, particleSystem.height
  )
  
  const hourColor = getHourColor(hourProgress)
  gradient.addColorStop(0, `rgba(${hourColor.r}, ${hourColor.g}, ${hourColor.b}, 0.1)`)
  gradient.addColorStop(1, `rgba(${hourColor.r + 20}, ${hourColor.g + 20}, ${hourColor.b + 40}, 0.1)`)
  
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, particleSystem.width, particleSystem.height)

  const flowLines = 20
  for (let i = 0; i < flowLines; i++) {
    const y = (i / flowLines) * particleSystem.height
    const waveOffset = Math.sin(Date.now() * 0.002 + i * 0.5) * 20
    const flowSpeed = (trafficValue / 100) * 3

    ctx.beginPath()
    ctx.moveTo(0, y)
    
    for (let x = 0; x < particleSystem.width; x += 10) {
      const waveY = y + Math.sin((x + Date.now() * 0.001 * flowSpeed) * 0.05) * 10 + waveOffset
      ctx.lineTo(x, waveY)
    }

    const lineColor = getColorForValue(trafficValue, 'traffic')
    ctx.strokeStyle = `rgba(${lineColor.r}, ${lineColor.g}, ${lineColor.b}, 0.3)`
    ctx.lineWidth = 1
    ctx.stroke()
  }

  particleSystem.particles.forEach(particle => {
    particle.update(hourProgress, trafficValue, aqiValue)
    particle.draw(ctx, hourProgress)
  })

  drawTimeDistribution(ctx, hourProgress)
}

const getHourColor = (hourProgress) => {
  const hour = hourProgress * 24
  
  if (hour >= 6 && hour < 18) {
    return { r: 20, g: 30, b: 60 }
  } else {
    return { r: 10, g: 15, b: 40 }
  }
}

const drawTimeDistribution = (ctx, hourProgress) => {
  if (!particleSystem) return

  const barWidth = particleSystem.width / 24
  const maxBarHeight = particleSystem.height * 0.15

  ctx.save()
  ctx.translate(0, particleSystem.height - maxBarHeight - 20)

  for (let hour = 0; hour < 24; hour++) {
    const hourData = hourlyData.value.find(d => Math.floor(d.hour) === hour)
    const trafficValue = hourData?.traffic_index || 50
    const barHeight = (trafficValue / 100) * maxBarHeight

    const x = hour * barWidth
    
    const isCurrentHour = Math.abs(hour - hourProgress * 24) < 0.5
    const color = isCurrentHour 
      ? getColorForValue(trafficValue, 'traffic')
      : { r: 100, g: 100, b: 150 }

    const alpha = isCurrentHour ? 0.8 : 0.4

    ctx.fillStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha})`
    ctx.fillRect(x + 2, maxBarHeight - barHeight, barWidth - 4, barHeight)

    if (hour % 6 === 0) {
      ctx.fillStyle = 'rgba(255, 255, 255, 0.5)'
      ctx.font = '10px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(`${hour}:00`, x + barWidth / 2, maxBarHeight + 15)
    }
  }

  const currentX = hourProgress * 24 * barWidth + barWidth / 2
  ctx.beginPath()
  ctx.moveTo(currentX, -10)
  ctx.lineTo(currentX - 5, 0)
  ctx.lineTo(currentX + 5, 0)
  ctx.closePath()
  ctx.fillStyle = 'rgba(255, 255, 255, 0.8)'
  ctx.fill()

  ctx.restore()
}

const animate = () => {
  if (!canvasContext || !particleSystem) {
    animationFrameId = requestAnimationFrame(animate)
    return
  }

  const hourProgress = currentHour.value / 24
  
  const currentHourData = getInterpolatedData(currentHour.value)
  const trafficValue = currentHourData.traffic_index
  const aqiValue = currentHourData.aqi

  canvasContext.clearRect(0, 0, particleSystem.width, particleSystem.height)

  drawFluidEffect(canvasContext, hourProgress, trafficValue, aqiValue)

  animationFrameId = requestAnimationFrame(animate)
}

const getInterpolatedData = (hour) => {
  if (hourlyData.value.length === 0) {
    return { traffic_index: 50, aqi: 50 }
  }

  const lowerHour = Math.floor(hour)
  const upperHour = Math.min(lowerHour + 1, 23)
  const progress = hour - lowerHour

  const lowerData = hourlyData.value.find(d => Math.floor(d.hour) === lowerHour)
  const upperData = hourlyData.value.find(d => Math.floor(d.hour) === upperHour)

  if (!lowerData || !upperData) {
    return lowerData || upperData || { traffic_index: 50, aqi: 50 }
  }

  return {
    traffic_index: lowerData.traffic_index * (1 - progress) + upperData.traffic_index * progress,
    aqi: lowerData.aqi * (1 - progress) + upperData.aqi * progress
  }
}

const loadData = async () => {
  try {
    hourlyData.value = await dataService.getHourlyData(props.city)
    
    if (hourlyData.value.length === 0) {
      generateMockData()
    }
  } catch (error) {
    console.error('加载数据失败:', error)
    generateMockData()
  }
}

const generateMockData = () => {
  hourlyData.value = []
  for (let hour = 0; hour < 24; hour++) {
    let trafficValue = 50
    
    if (hour >= 7 && hour <= 10) {
      trafficValue = 70 + Math.sin((hour - 7) / 3 * Math.PI) * 20
    } else if (hour >= 17 && hour <= 20) {
      trafficValue = 75 + Math.sin((hour - 17) / 3 * Math.PI) * 15
    } else if (hour >= 0 && hour <= 5) {
      trafficValue = 20 + Math.random() * 10
    } else {
      trafficValue = 40 + Math.random() * 20
    }

    let aqiValue = 60
    if (hour >= 7 && hour <= 11) {
      aqiValue = 70 + Math.sin((hour - 7) / 4 * Math.PI) * 30
    } else if (hour >= 18 && hour <= 22) {
      aqiValue = 65 + Math.sin((hour - 18) / 4 * Math.PI) * 25
    } else {
      aqiValue = 50 + Math.random() * 20
    }

    hourlyData.value.push({
      hour,
      traffic_index: trafficValue,
      aqi: aqiValue
    })
  }
}

const togglePlay = () => {
  isPlaying.value = !isPlaying.value
  
  if (isPlaying.value) {
    playInterval = setInterval(() => {
      currentHour.value += 0.1
      if (currentHour.value >= 24) {
        currentHour.value = 0
      }
      updateActiveStep()
    }, 100)
  } else {
    if (playInterval) {
      clearInterval(playInterval)
      playInterval = null
    }
  }
}

const resetTimeline = () => {
  currentHour.value = 0
  if (isPlaying.value) {
    togglePlay()
  }
  updateActiveStep()
}

const updateActiveStep = () => {
  const stepHours = steps.value.map(s => s.hour)
  let closestIndex = 0
  let minDiff = Infinity

  stepHours.forEach((hour, index) => {
    const diff = Math.abs(currentHour.value - hour)
    if (diff < minDiff) {
      minDiff = diff
      closestIndex = index
    }
  })

  activeStep.value = closestIndex
}

const handleScroll = () => {
  if (!scrollContainer.value) return

  const container = scrollContainer.value
  const scrollProgress = container.scrollTop / (container.scrollHeight - container.clientHeight)
  
  currentHour.value = scrollProgress * 24
  updateActiveStep()
}

watch(() => props.city, () => {
  loadData()
})

watch(currentHour, () => {
  updateActiveStep()
})

onMounted(() => {
  nextTick(() => {
    initCanvas()
    animate()
    loadData()
  })

  window.addEventListener('resize', () => {
    if (particleCanvas.value) {
      const container = particleCanvas.value.parentElement
      particleCanvas.value.width = container.clientWidth
      particleCanvas.value.height = container.clientHeight
      
      if (particleSystem) {
        particleSystem.width = particleCanvas.value.width
        particleSystem.height = particleCanvas.value.height
        particleSystem.particles.forEach(p => {
          p.canvasWidth = particleCanvas.value.width
          p.canvasHeight = particleCanvas.value.height
        })
      }
    }
  })
})

onUnmounted(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
  if (playInterval) {
    clearInterval(playInterval)
  }
})
</script>

<style scoped>
.timeline-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: rgba(10, 10, 30, 0.95);
}

.timeline-header {
  padding: 15px 30px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.timeline-header h2 {
  margin: 0 0 10px 0;
  font-size: 1.3rem;
  color: rgba(255, 255, 255, 0.9);
}

.time-indicator {
  display: flex;
  align-items: center;
  gap: 15px;
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.7);
  position: relative;
  padding: 5px 0;
}

.time-indicator .highlight {
  font-weight: bold;
  color: #667eea;
  font-size: 1.1rem;
}

.time-marker {
  position: absolute;
  bottom: 0;
  width: 2px;
  height: 3px;
  background: #667eea;
  transition: left 0.3s ease;
}

.scrollytelling-container {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
}

.canvas-wrapper {
  flex: 1;
  position: relative;
  background: linear-gradient(135deg, #0a0a1e 0%, #1a1a3e 100%);
}

.particle-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.canvas-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.current-hour-label {
  position: absolute;
  top: 20px;
  right: 30px;
  font-size: 2rem;
  font-weight: bold;
  color: rgba(255, 255, 255, 0.3);
  text-shadow: 0 0 20px rgba(102, 126, 234, 0.5);
}

.scroll-steps {
  width: 350px;
  padding: 20px;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.3);
}

.step-section {
  padding: 20px;
  margin-bottom: 30px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.5s ease;
}

.step-section.active {
  background: rgba(102, 126, 234, 0.15);
  border-color: rgba(102, 126, 234, 0.5);
}

.step-content h3 {
  margin: 0 0 10px 0;
  font-size: 1.1rem;
  color: rgba(255, 255, 255, 0.9);
}

.step-content p {
  margin: 0 0 15px 0;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.5;
}

.step-metrics {
  display: flex;
  gap: 15px;
}

.step-metric {
  flex: 1;
  padding: 10px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  text-align: center;
}

.step-metric .metric-name {
  display: block;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 5px;
}

.step-metric .metric-value {
  font-size: 1.2rem;
  font-weight: bold;
}

.step-metric .metric-value.good { color: #00c853; }
.step-metric .metric-value.moderate { color: #ffab00; }
.step-metric .metric-value.bad { color: #ff3d00; }
.step-metric .metric-value.aqi-good { color: #00e400; }
.step-metric .metric-value.aqi-moderate { color: #ffff00; }
.step-metric .metric-value.aqi-bad { color: #ff7e00; }
.step-metric .metric-value.aqi-severe { color: #ff0000; }

.timeline-controls {
  padding: 15px 30px;
  background: rgba(0, 0, 0, 0.4);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.time-slider-container {
  margin-bottom: 15px;
}

.time-slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.1);
  outline: none;
  -webkit-appearance: none;
  cursor: pointer;
}

.time-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  cursor: pointer;
  box-shadow: 0 0 10px rgba(102, 126, 234, 0.5);
  transition: transform 0.2s ease;
}

.time-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.5);
}

.play-controls {
  display: flex;
  gap: 15px;
  justify-content: center;
}

.play-btn, .reset-btn {
  padding: 10px 25px;
  border-radius: 25px;
  border: none;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.play-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.play-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
}

.reset-btn {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.reset-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
}
</style>
