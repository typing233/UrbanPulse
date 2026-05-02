<template>
  <div class="timeline-container">
    <div class="timeline-header">
      <h2>{{ city }} - 24小时数据演变</h2>
      <div class="time-indicator">
        当前时间: <span class="highlight">{{ currentTime }}</span>
      </div>
    </div>

    <div class="scrollytelling-container">
      <div class="canvas-wrapper">
        <canvas ref="particleCanvas" class="particle-canvas"></canvas>
        <canvas ref="trailCanvas" class="trail-canvas"></canvas>
        <div class="canvas-overlay">
          <div class="current-hour-label">
            {{ Math.floor(currentHour) }}:{{ String(Math.floor((currentHour % 1) * 60)).padStart(2, '0') }}
          </div>
        </div>
      </div>

      <div class="scroll-steps">
        <div 
          v-for="(step, index) in steps" 
          :key="index"
          class="step-section"
          :class="{ active: activeStep === index }"
          @click="jumpToStep(step.hour)"
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
          step="0.01"
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
        <button @click="toggleSlowMotion" class="speed-btn" :class="{ active: slowMotion }">
          {{ slowMotion ? '⏩ 正常' : '⏱️ 慢放' }}
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
const trailCanvas = ref(null)

const hourlyData = ref([])
const currentHour = ref(0)
const isPlaying = ref(false)
const slowMotion = ref(false)
const activeStep = ref(0)

let animationFrameId = null
let playInterval = null
let mainCtx = null
let trailCtx = null
let canvasWidth = 0
let canvasHeight = 0

let velocityField = null
let particles = []
let time = 0

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

const initVelocityField = () => {
  const gridSize = 20
  const cellSizeX = canvasWidth / gridSize
  const cellSizeY = canvasHeight / gridSize
  
  velocityField = {
    gridSize,
    cellSizeX,
    cellSizeY,
    velocities: []
  }
  
  for (let y = 0; y < gridSize; y++) {
    velocityField.velocities[y] = []
    for (let x = 0; x < gridSize; x++) {
      const flowAngles = getFlowAnglesForPosition(x, y, gridSize)
      velocityField.velocities[y][x] = {
        baseVx: Math.cos(flowAngles.angle1) * flowAngles.strength1,
        baseVy: Math.sin(flowAngles.angle1) * flowAngles.strength1,
        secondaryVx: Math.cos(flowAngles.angle2) * flowAngles.strength2,
        secondaryVy: Math.sin(flowAngles.angle2) * flowAngles.strength2
      }
    }
  }
}

const getFlowAnglesForPosition = (x, y, gridSize) => {
  const centerX = gridSize / 2
  const centerY = gridSize / 2
  
  const dx = x - centerX
  const dy = y - centerY
  
  const distance = Math.sqrt(dx * dx + dy * dy)
  
  let angle1 = 0
  let strength1 = 1
  let angle2 = 0
  let strength2 = 0.5
  
  if (distance < 3) {
    angle1 = (dx < 0 ? Math.PI : 0) + (dy < 0 ? Math.PI / 4 : -Math.PI / 4)
    strength1 = 1.5
  } else if (x < gridSize * 0.25) {
    angle1 = Math.PI / 6
    strength1 = 1.2
  } else if (x > gridSize * 0.75) {
    angle1 = -Math.PI / 6
    strength1 = 1.2
  } else if (y < gridSize * 0.25) {
    angle1 = Math.PI / 3
    strength1 = 1.0
  } else if (y > gridSize * 0.75) {
    angle1 = -Math.PI / 3
    strength1 = 1.0
  } else {
    angle1 = (dx > 0 ? -0.2 : 0.2)
    strength1 = 0.8
  }
  
  angle2 = angle1 + Math.PI / 2 + Math.sin(time * 0.5) * 0.3
  
  return { angle1, strength1, angle2, strength2 }
}

const getVelocityAt = (x, y, hourProgress, trafficMultiplier) => {
  if (!velocityField) return { vx: 0, vy: 0 }
  
  const gridX = Math.floor(x / velocityField.cellSizeX)
  const gridY = Math.floor(y / velocityField.cellSizeY)
  
  const clampedX = Math.max(0, Math.min(velocityField.gridSize - 1, gridX))
  const clampedY = Math.max(0, Math.min(velocityField.gridSize - 1, gridY))
  
  const velocity = velocityField.velocities[clampedY][clampedX]
  
  const t = hourProgress * Math.PI * 2
  const swirlFactor = Math.sin(t) * 0.3 + Math.cos(t * 1.5) * 0.2
  
  const timeVaryingVx = velocity.baseVx + velocity.secondaryVx * swirlFactor
  const timeVaryingVy = velocity.baseVy + velocity.secondaryVy * swirlFactor
  
  const distToCenterX = Math.abs(x - canvasWidth / 2) / (canvasWidth / 2)
  const distToCenterY = Math.abs(y - canvasHeight / 2) / (canvasHeight / 2)
  const edgeBoost = 1 + (distToCenterX + distToCenterY) * 0.5
  
  return {
    vx: timeVaryingVx * trafficMultiplier * edgeBoost,
    vy: timeVaryingVy * trafficMultiplier * edgeBoost
  }
}

class FluidParticle {
  constructor(x, y) {
    this.x = x
    this.y = y
    this.vx = 0
    this.vy = 0
    
    this.trail = []
    this.maxTrailLength = 40
    
    this.baseRadius = 1.5 + Math.random() * 2.5
    this.radius = this.baseRadius
    
    this.hue = 0.5 + Math.random() * 0.2
    this.saturation = 0.8
    this.baseAlpha = 0.6 + Math.random() * 0.3
    
    this.lifeTime = Math.random() * 1000
    this.type = Math.random() > 0.7 ? 'fast' : 'normal'
    
    this.targetX = x
    this.targetY = y
  }
  
  update(hourProgress, trafficValue, aqiValue, dt) {
    this.lifeTime += dt
    
    const trafficMultiplier = 0.3 + (trafficValue / 100) * 1.5
    const velocity = getVelocityAt(this.x, this.y, hourProgress, trafficMultiplier)
    
    const accelerationX = velocity.vx - this.vx
    const accelerationY = velocity.vy - this.vy
    
    const damping = this.type === 'fast' ? 0.15 : 0.1
    this.vx += accelerationX * damping
    this.vy += accelerationY * damping
    
    const turbulence = (Math.random() - 0.5) * 0.5 * trafficMultiplier
    this.vx += turbulence
    this.vy += turbulence
    
    const maxSpeed = this.type === 'fast' ? 6 : 3.5
    const speed = Math.sqrt(this.vx * this.vx + this.vy * this.vy)
    if (speed > maxSpeed) {
      const scale = maxSpeed / speed
      this.vx *= scale
      this.vy *= scale
    }
    
    this.x += this.vx * dt
    this.y += this.vy * dt
    
    if (this.x < 0) this.x = canvasWidth
    if (this.x > canvasWidth) this.x = 0
    if (this.y < 0) this.y = canvasHeight
    if (this.y > canvasHeight) this.y = 0
    
    if (this.trail.length === 0 || 
        Math.abs(this.x - this.trail[this.trail.length - 1].x) > 0.5 ||
        Math.abs(this.y - this.trail[this.trail.length - 1].y) > 0.5) {
      this.trail.push({
        x: this.x,
        y: this.y,
        age: 0
      })
    }
    
    if (this.trail.length > this.maxTrailLength) {
      this.trail.shift()
    }
    
    this.trail.forEach(point => {
      point.age += dt
    })
    
    const pulse = 0.8 + Math.sin(this.lifeTime * 0.003 + this.x * 0.01) * 0.2
    this.radius = this.baseRadius * pulse * (0.8 + (trafficValue / 100) * 0.4)
    
    const trafficColor = getColorForValue(trafficValue, 'traffic')
    const aqiColor = getColorForValue(aqiValue, 'aqi')
    
    const colorMix = hourProgress
    this.r = Math.floor(trafficColor.r * (1 - colorMix) + aqiColor.r * colorMix)
    this.g = Math.floor(trafficColor.g * (1 - colorMix) + aqiColor.g * colorMix)
    this.b = Math.floor(trafficColor.b * (1 - colorMix) + aqiColor.b * colorMix)
  }
  
  drawTrail(ctx) {
    if (this.trail.length < 3) return
    
    for (let i = 1; i < this.trail.length; i++) {
      const prevPoint = this.trail[i - 1]
      const currentPoint = this.trail[i]
      
      const progress = i / this.trail.length
      const alpha = progress * this.baseAlpha
      const width = this.radius * 0.8 * progress
      
      ctx.beginPath()
      ctx.moveTo(prevPoint.x, prevPoint.y)
      ctx.lineTo(currentPoint.x, currentPoint.y)
      
      const gradient = ctx.createLinearGradient(
        prevPoint.x, prevPoint.y,
        currentPoint.x, currentPoint.y
      )
      gradient.addColorStop(0, `rgba(${this.r}, ${this.g}, ${this.b}, ${alpha * 0.3})`)
      gradient.addColorStop(1, `rgba(${this.r}, ${this.g}, ${this.b}, ${alpha})`)
      
      ctx.strokeStyle = gradient
      ctx.lineWidth = width
      ctx.lineCap = 'round'
      ctx.stroke()
    }
  }
  
  drawParticle(ctx) {
    const speed = Math.sqrt(this.vx * this.vx + this.vy * this.vy)
    const speedFactor = Math.min(1, speed / 4)
    
    const glowRadius = this.radius * (2 + speedFactor)
    const gradient = ctx.createRadialGradient(
      this.x, this.y, 0,
      this.x, this.y, glowRadius
    )
    
    const alpha = this.baseAlpha * (0.5 + speedFactor * 0.5)
    gradient.addColorStop(0, `rgba(${this.r}, ${this.g}, ${this.b}, ${alpha})`)
    gradient.addColorStop(0.3, `rgba(${this.r}, ${this.g}, ${this.b}, ${alpha * 0.5})`)
    gradient.addColorStop(1, `rgba(${this.r}, ${this.g}, ${this.b}, 0)`)
    
    ctx.beginPath()
    ctx.arc(this.x, this.y, glowRadius, 0, Math.PI * 2)
    ctx.fillStyle = gradient
    ctx.fill()
    
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(255, 255, 255, ${this.baseAlpha * 0.8})`
    ctx.fill()
  }
}

const initCanvas = () => {
  if (!particleCanvas.value || !trailCanvas.value) return

  const canvas = particleCanvas.value
  const trail = trailCanvas.value
  const container = canvas.parentElement

  canvasWidth = container.clientWidth
  canvasHeight = container.clientHeight

  canvas.width = canvasWidth
  canvas.height = canvasHeight
  trail.width = canvasWidth
  trail.height = canvasHeight

  mainCtx = canvas.getContext('2d')
  trailCtx = trail.getContext('2d')

  initVelocityField()
  initParticles()
}

const initParticles = () => {
  particles = []
  const particleCount = 250
  
  for (let i = 0; i < particleCount; i++) {
    const x = Math.random() * canvasWidth
    const y = Math.random() * canvasHeight
    particles.push(new FluidParticle(x, y))
  }
}

const drawBackground = (ctx, hourProgress, trafficValue, aqiValue) => {
  const hour = hourProgress * 24
  let bgColor1, bgColor2
  
  if (hour >= 6 && hour < 8) {
    const t = (hour - 6) / 2
    bgColor1 = `rgb(${Math.floor(10 + t * 20)}, ${Math.floor(15 + t * 30)}, ${Math.floor(30 + t * 40)})`
    bgColor2 = `rgb(${Math.floor(20 + t * 40)}, ${Math.floor(25 + t * 50)}, ${Math.floor(50 + t * 60)})`
  } else if (hour >= 8 && hour < 17) {
    bgColor1 = 'rgb(30, 45, 70)'
    bgColor2 = 'rgb(60, 75, 110)'
  } else if (hour >= 17 && hour < 19) {
    const t = (hour - 17) / 2
    bgColor1 = `rgb(${Math.floor(30 - t * 20)}, ${Math.floor(45 - t * 30)}, ${Math.floor(70 - t * 40)})`
    bgColor2 = `rgb(${Math.floor(60 - t * 40)}, ${Math.floor(75 - t * 50)}, ${Math.floor(110 - t * 60)})`
  } else {
    bgColor1 = 'rgb(10, 15, 30)'
    bgColor2 = 'rgb(20, 25, 50)'
  }
  
  const gradient = ctx.createLinearGradient(0, 0, canvasWidth, canvasHeight)
  gradient.addColorStop(0, bgColor1)
  gradient.addColorStop(1, bgColor2)
  
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, canvasWidth, canvasHeight)
  
  drawFlowLines(ctx, hourProgress, trafficValue)
}

const drawFlowLines = (ctx, hourProgress, trafficValue) => {
  const lineCount = 15
  const trafficMultiplier = 0.3 + (trafficValue / 100) * 1.5
  
  for (let i = 0; i < lineCount; i++) {
    const y = (i / lineCount) * canvasHeight
    
    ctx.beginPath()
    ctx.moveTo(0, y)
    
    for (let x = 0; x < canvasWidth; x += 5) {
      const velocity = getVelocityAt(x, y, hourProgress, trafficMultiplier)
      const waveY = y + velocity.vy * 3 + Math.sin((x + time * 50) * 0.01) * 15
      ctx.lineTo(x, waveY)
    }
    
    const trafficColor = getColorForValue(trafficValue, 'traffic')
    const alpha = 0.1 + (i / lineCount) * 0.15
    
    ctx.strokeStyle = `rgba(${trafficColor.r}, ${trafficColor.g}, ${trafficColor.b}, ${alpha})`
    ctx.lineWidth = 1
    ctx.stroke()
  }
}

const drawTimeDistribution = (ctx, hourProgress) => {
  const barWidth = canvasWidth / 24
  const maxBarHeight = canvasHeight * 0.12
  const bottomY = canvasHeight - maxBarHeight - 30
  
  ctx.save()
  
  for (let hour = 0; hour < 24; hour++) {
    const hourData = hourlyData.value.find(d => Math.floor(d.hour) === hour)
    const trafficValue = hourData?.traffic_index || 50
    const barHeight = (trafficValue / 100) * maxBarHeight
    
    const x = hour * barWidth
    
    const isCurrentHour = Math.abs(hour - hourProgress * 24) < 0.5
    const isNearHour = Math.abs(hour - hourProgress * 24) < 2
    
    const color = isCurrentHour 
      ? getColorForValue(trafficValue, 'traffic')
      : isNearHour
        ? getColorForValue(trafficValue, 'traffic')
        : { r: 80, g: 80, b: 120 }

    const alpha = isCurrentHour ? 0.9 : isNearHour ? 0.5 : 0.2
    
    ctx.fillStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha})`
    ctx.fillRect(x + 3, bottomY - barHeight, barWidth - 6, barHeight)
    
    if (isCurrentHour) {
      const highlightGradient = ctx.createLinearGradient(x, bottomY - barHeight, x, bottomY)
      highlightGradient.addColorStop(0, `rgba(255, 255, 255, 0.3)`)
      highlightGradient.addColorStop(1, `rgba(255, 255, 255, 0)`)
      ctx.fillStyle = highlightGradient
      ctx.fillRect(x + 3, bottomY - barHeight, barWidth - 6, barHeight * 0.3)
    }
    
    if (hour % 6 === 0) {
      ctx.fillStyle = 'rgba(255, 255, 255, 0.6)'
      ctx.font = '11px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(`${hour}:00`, x + barWidth / 2, bottomY + maxBarHeight + 15)
    }
  }
  
  const currentX = hourProgress * 24 * barWidth + barWidth / 2
  const arrowSize = 8
  
  ctx.beginPath()
  ctx.moveTo(currentX, bottomY - maxBarHeight - 15)
  ctx.lineTo(currentX - arrowSize, bottomY - maxBarHeight - 5)
  ctx.lineTo(currentX + arrowSize, bottomY - maxBarHeight - 5)
  ctx.closePath()
  ctx.fillStyle = 'rgba(255, 255, 255, 0.9)'
  ctx.fill()
  
  ctx.beginPath()
  ctx.moveTo(currentX, bottomY - maxBarHeight - 15)
  ctx.lineTo(currentX, bottomY)
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)'
  ctx.lineWidth = 2
  ctx.setLineDash([5, 5])
  ctx.stroke()
  ctx.setLineDash([])
  
  ctx.restore()
}

const animate = () => {
  if (!mainCtx || !trailCtx) {
    animationFrameId = requestAnimationFrame(animate)
    return
  }

  const dt = slowMotion.value ? 0.016 : 0.016 * 2
  time += dt
  
  const hourProgress = currentHour.value / 24
  const currentHourData = getInterpolatedData(currentHour.value)
  const trafficValue = currentHourData.traffic_index
  const aqiValue = currentHourData.aqi
  
  trailCtx.clearRect(0, 0, canvasWidth, canvasHeight)
  
  trailCtx.fillStyle = 'rgba(10, 15, 30, 0.15)'
  trailCtx.fillRect(0, 0, canvasWidth, canvasHeight)
  
  particles.forEach(particle => {
    particle.update(hourProgress, trafficValue, aqiValue, dt)
    particle.drawTrail(trailCtx)
  })
  
  mainCtx.clearRect(0, 0, canvasWidth, canvasHeight)
  
  drawBackground(mainCtx, hourProgress, trafficValue, aqiValue)
  
  mainCtx.drawImage(trailCanvas.value, 0, 0)
  
  particles.forEach(particle => {
    particle.drawParticle(mainCtx)
  })
  
  drawTimeDistribution(mainCtx, hourProgress)

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
    const interval = slowMotion.value ? 200 : 100
    playInterval = setInterval(() => {
      currentHour.value += 0.1
      if (currentHour.value >= 24) {
        currentHour.value = 0
      }
      updateActiveStep()
    }, interval)
  } else {
    if (playInterval) {
      clearInterval(playInterval)
      playInterval = null
    }
  }
}

const toggleSlowMotion = () => {
  slowMotion.value = !slowMotion.value
  
  if (isPlaying.value && playInterval) {
    clearInterval(playInterval)
    const interval = slowMotion.value ? 200 : 100
    playInterval = setInterval(() => {
      currentHour.value += 0.1
      if (currentHour.value >= 24) {
        currentHour.value = 0
      }
      updateActiveStep()
    }, interval)
  }
}

const resetTimeline = () => {
  currentHour.value = 0
  if (isPlaying.value) {
    togglePlay()
  }
  updateActiveStep()
}

const jumpToStep = (hour) => {
  currentHour.value = hour
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
    if (particleCanvas.value && trailCanvas.value) {
      const container = particleCanvas.value.parentElement
      canvasWidth = container.clientWidth
      canvasHeight = container.clientHeight
      
      particleCanvas.value.width = canvasWidth
      particleCanvas.value.height = canvasHeight
      trailCanvas.value.width = canvasWidth
      trailCanvas.value.height = canvasHeight
      
      initVelocityField()
      initParticles()
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
}

.time-indicator .highlight {
  font-weight: bold;
  color: #667eea;
  font-size: 1.1rem;
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
  position: absolute;
  top: 0;
  left: 0;
  z-index: 2;
}

.trail-canvas {
  width: 100%;
  height: 100%;
  display: block;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
}

.canvas-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 3;
}

.current-hour-label {
  position: absolute;
  top: 20px;
  right: 30px;
  font-size: 2rem;
  font-weight: bold;
  color: rgba(255, 255, 255, 0.3);
  text-shadow: 0 0 20px rgba(102, 126, 234, 0.5);
  font-family: 'Courier New', monospace;
}

.scroll-steps {
  width: 350px;
  padding: 20px;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.3);
  z-index: 10;
}

.step-section {
  padding: 20px;
  margin-bottom: 30px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.5s ease;
  cursor: pointer;
}

.step-section:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.15);
}

.step-section.active {
  background: rgba(102, 126, 234, 0.15);
  border-color: rgba(102, 126, 234, 0.5);
  transform: translateX(5px);
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
  height: 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
  outline: none;
  -webkit-appearance: none;
  cursor: pointer;
}

.time-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  cursor: pointer;
  box-shadow: 0 0 15px rgba(102, 126, 234, 0.6);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.time-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
  box-shadow: 0 0 25px rgba(102, 126, 234, 0.8);
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

.play-btn, .reset-btn, .speed-btn {
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

.speed-btn {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.speed-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.speed-btn.active {
  background: rgba(102, 126, 234, 0.2);
  border-color: rgba(102, 126, 234, 0.5);
  color: #667eea;
}
</style>
