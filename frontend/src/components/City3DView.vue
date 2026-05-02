<template>
  <div class="city-3d-container">
    <div ref="container" class="canvas-container"></div>
    <div class="info-panel">
      <h3>{{ city }} - 实时数据</h3>
      <div class="metric-row">
        <span class="label">🚗 交通拥堵:</span>
        <span class="value" :class="getTrafficClass(currentData?.traffic_index)">
          {{ currentData?.traffic_index || '--' }}
        </span>
        <span class="status">{{ currentData?.traffic_level || '加载中' }}</span>
      </div>
      <div class="metric-row">
        <span class="label">🌬️ 空气质量:</span>
        <span class="value" :class="getAQIClass(currentData?.aqi)">
          {{ currentData?.aqi || '--' }}
        </span>
        <span class="status">{{ currentData?.aqi_level?.[0] || '加载中' }}</span>
      </div>
      <div class="controls">
        <button @click="toggleAutoRotate" class="control-btn">
          {{ autoRotate ? '停止旋转' : '自动旋转' }}
        </button>
        <button @click="resetCamera" class="control-btn">重置视角</button>
      </div>
    </div>
    <div class="legend">
      <h4>图例</h4>
      <div class="legend-item">
        <div class="legend-color" style="background: #00c853"></div>
        <span>畅通/优</span>
      </div>
      <div class="legend-item">
        <div class="legend-color" style="background: #ffab00"></div>
        <span>轻度拥堵/良</span>
      </div>
      <div class="legend-item">
        <div class="legend-color" style="background: #ff3d00"></div>
        <span>拥堵/污染</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { dataService } from '../utils/dataService'
import { AnomalyDetector } from '../utils/anomalyDetector'

const props = defineProps({
  city: {
    type: String,
    default: '北京'
  }
})

const emit = defineEmits(['anomaly'])

const container = ref(null)
const currentData = ref(null)
const districtData = ref([])
const autoRotate = ref(true)

let scene = null
let camera = null
let renderer = null
let controls = null
let buildings = []
let roads = []
let particles = []
let rippleEffects = []
let animationId = null
let dataUpdateInterval = null
let anomalyDetector = null

const cityConfigs = {
  '北京': {
    center: { lat: 39.9042, lon: 116.4074 },
    gridSize: 15,
    buildingDensity: 0.6,
    districts: [
      { name: '朝阳区', x: 3, z: 2, weight: 1.3 },
      { name: '海淀区', x: -3, z: 1, weight: 1.2 },
      { name: '东城区', x: 1, z: 0, weight: 1.0 },
      { name: '西城区', x: -1, z: 0, weight: 1.0 },
      { name: '丰台区', x: -2, z: -2, weight: 0.9 }
    ]
  },
  '上海': {
    center: { lat: 31.2304, lon: 121.4737 },
    gridSize: 15,
    buildingDensity: 0.7,
    districts: [
      { name: '浦东新区', x: 3, z: 1, weight: 1.3 },
      { name: '黄浦区', x: 0, z: 0, weight: 1.2 },
      { name: '徐汇区', x: -1, z: -1, weight: 1.1 },
      { name: '静安区', x: -1, z: 1, weight: 1.0 },
      { name: '长宁区', x: -2, z: 0, weight: 0.9 }
    ]
  }
}

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
    if (value < 30) return new THREE.Color(0x00c853)
    if (value < 50) return new THREE.Color(0x64dd17)
    if (value < 70) return new THREE.Color(0xffab00)
    if (value < 90) return new THREE.Color(0xff6d00)
    return new THREE.Color(0xff3d00)
  } else {
    if (value <= 50) return new THREE.Color(0x00e400)
    if (value <= 100) return new THREE.Color(0xffff00)
    if (value <= 150) return new THREE.Color(0xff7e00)
    if (value <= 200) return new THREE.Color(0xff0000)
    if (value <= 300) return new THREE.Color(0x99004c)
    return new THREE.Color(0x7e0023)
  }
}

const initScene = () => {
  const config = cityConfigs[props.city] || cityConfigs['北京']
  const width = container.value.clientWidth
  const height = container.value.clientHeight

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a0a1a)
  scene.fog = new THREE.Fog(0x0a0a1a, 30, 100)

  camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000)
  camera.position.set(25, 20, 25)

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  container.value.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.minDistance = 10
  controls.maxDistance = 80
  controls.maxPolarAngle = Math.PI / 2.2

  const ambientLight = new THREE.AmbientLight(0x404060, 0.6)
  scene.add(ambientLight)

  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
  directionalLight.position.set(20, 40, 20)
  directionalLight.castShadow = true
  directionalLight.shadow.mapSize.width = 2048
  directionalLight.shadow.mapSize.height = 2048
  directionalLight.shadow.camera.near = 0.5
  directionalLight.shadow.camera.far = 100
  directionalLight.shadow.camera.left = -30
  directionalLight.shadow.camera.right = 30
  directionalLight.shadow.camera.top = 30
  directionalLight.shadow.camera.bottom = -30
  scene.add(directionalLight)

  const pointLight1 = new THREE.PointLight(0x667eea, 1, 50)
  pointLight1.position.set(-15, 15, -15)
  scene.add(pointLight1)

  const pointLight2 = new THREE.PointLight(0x764ba2, 1, 50)
  pointLight2.position.set(15, 15, 15)
  scene.add(pointLight2)

  createGround(config)
  createRoads(config)
  createBuildings(config)
  createParticles(config)

  window.addEventListener('resize', onWindowResize)

  animate()
}

const createGround = (config) => {
  const groundGeometry = new THREE.PlaneGeometry(60, 60)
  const groundMaterial = new THREE.MeshStandardMaterial({
    color: 0x1a1a2e,
    roughness: 0.8,
    metalness: 0.2
  })
  const ground = new THREE.Mesh(groundGeometry, groundMaterial)
  ground.rotation.x = -Math.PI / 2
  ground.receiveShadow = true
  scene.add(ground)

  const gridHelper = new THREE.GridHelper(60, 60, 0x333366, 0x222244)
  gridHelper.position.y = 0.01
  scene.add(gridHelper)
}

const createRoads = (config) => {
  const roadMaterial = new THREE.MeshStandardMaterial({
    color: 0x2a2a3e,
    roughness: 0.9,
    metalness: 0.1
  })

  for (let i = 0; i < 5; i++) {
    const roadGeometry = new THREE.BoxGeometry(55, 0.1, 2)
    const road = new THREE.Mesh(roadGeometry, roadMaterial)
    road.position.set(0, 0.05, (i - 2) * 12)
    road.receiveShadow = true
    scene.add(road)
    roads.push({ mesh: road, trafficFlow: 0.5, baseZ: (i - 2) * 12, direction: i % 2 === 0 ? 1 : -1 })

    const roadGeometry2 = new THREE.BoxGeometry(2, 0.1, 55)
    const road2 = new THREE.Mesh(roadGeometry2, roadMaterial)
    road2.position.set((i - 2) * 12, 0.05, 0)
    road2.receiveShadow = true
    scene.add(road2)
    roads.push({ mesh: road2, trafficFlow: 0.5, baseX: (i - 2) * 12, direction: i % 2 === 0 ? 1 : -1 })
  }

  createRoadLights()
}

const createRoadLights = () => {
  for (let i = -2; i <= 2; i++) {
    for (let j = -2; j <= 2; j++) {
      const poleGeometry = new THREE.CylinderGeometry(0.05, 0.05, 2)
      const poleMaterial = new THREE.MeshStandardMaterial({ color: 0x444444 })
      const pole = new THREE.Mesh(poleGeometry, poleMaterial)
      pole.position.set(i * 12 + 5, 1, j * 12 + 5)
      scene.add(pole)

      const lightGeometry = new THREE.SphereGeometry(0.15, 8, 8)
      const lightMaterial = new THREE.MeshBasicMaterial({ color: 0xffff88 })
      const light = new THREE.Mesh(lightGeometry, lightMaterial)
      light.position.set(i * 12 + 5, 2, j * 12 + 5)
      scene.add(light)

      const pointLight = new THREE.PointLight(0xffff88, 0.3, 8)
      pointLight.position.copy(light.position)
      scene.add(pointLight)
    }
  }
}

const createBuildings = (config) => {
  buildings = []
  
  config.districts.forEach((district, di) => {
    const districtCenterX = district.x * 5
    const districtCenterZ = district.z * 5

    for (let i = 0; i < 20 * district.weight; i++) {
      const offsetX = (Math.random() - 0.5) * 8
      const offsetZ = (Math.random() - 0.5) * 8
      const x = districtCenterX + offsetX
      const z = districtCenterZ + offsetZ

      if (Math.abs(x % 12) < 2 || Math.abs(z % 12) < 2) continue

      const buildingHeight = 2 + Math.random() * 15
      const buildingWidth = 1 + Math.random() * 2
      const buildingDepth = 1 + Math.random() * 2

      const buildingGeometry = new THREE.BoxGeometry(buildingWidth, buildingHeight, buildingDepth)
      
      const buildingMaterial = new THREE.MeshStandardMaterial({
        color: 0x3a3a5e,
        roughness: 0.7,
        metalness: 0.3,
        emissive: 0x000000,
        emissiveIntensity: 0
      })

      const building = new THREE.Mesh(buildingGeometry, buildingMaterial)
      building.position.set(x, buildingHeight / 2, z)
      building.castShadow = true
      building.receiveShadow = true

      scene.add(building)

      const windows = createWindows(buildingWidth, buildingHeight, buildingDepth, x, z, buildingHeight)
      
      buildings.push({
        mesh: building,
        windows: windows,
        district: district.name,
        baseHeight: buildingHeight,
        targetHeight: buildingHeight,
        trafficValue: 50,
        aqiValue: 50,
        position: { x, z }
      })
    }
  })
}

const createWindows = (width, height, depth, x, z, buildingHeight) => {
  const windows = []
  const windowMaterial = new THREE.MeshBasicMaterial({ color: 0x4488ff, transparent: true, opacity: 0.8 })

  for (let floor = 1; floor < Math.floor(height / 1.5); floor++) {
    for (let w = 0; w < Math.floor(width * 2); w++) {
      const windowGeometry = new THREE.PlaneGeometry(0.3, 0.5)
      
      const window1 = new THREE.Mesh(windowGeometry, windowMaterial.clone())
      window1.position.set(
        x + (w - width) * 0.4,
        floor * 1.5 + 0.5,
        z + depth / 2 + 0.01
      )
      scene.add(window1)

      const window2 = new THREE.Mesh(windowGeometry, windowMaterial.clone())
      window2.position.set(
        x + (w - width) * 0.4,
        floor * 1.5 + 0.5,
        z - depth / 2 - 0.01
      )
      window2.rotation.y = Math.PI
      scene.add(window2)

      windows.push(window1, window2)
    }
  }

  return windows
}

const createParticles = (config) => {
  particles = []
  
  for (let i = 0; i < 200; i++) {
    const particleGeometry = new THREE.SphereGeometry(0.05, 4, 4)
    const particleMaterial = new THREE.MeshBasicMaterial({
      color: 0x66aaff,
      transparent: true,
      opacity: 0.6
    })

    const particle = new THREE.Mesh(particleGeometry, particleMaterial)
    particle.position.set(
      (Math.random() - 0.5) * 50,
      0.1 + Math.random() * 5,
      (Math.random() - 0.5) * 50
    )

    scene.add(particle)

    particles.push({
      mesh: particle,
      velocity: {
        x: (Math.random() - 0.5) * 0.05,
        z: (Math.random() - 0.5) * 0.05
      },
      baseY: particle.position.y
    })
  }
}

const updateBuildingsVisuals = () => {
  if (!districtData.value || districtData.value.length === 0) return

  buildings.forEach(building => {
    const districtInfo = districtData.value.find(d => d.district === building.district)
    
    if (districtInfo) {
      building.trafficValue = districtInfo.traffic_index || 50
      building.aqiValue = districtInfo.aqi || 50

      const trafficColor = getColorForValue(building.trafficValue, 'traffic')
      const aqiColor = getColorForValue(building.aqiValue, 'aqi')

      const finalColor = new THREE.Color()
      finalColor.lerpColors(trafficColor, aqiColor, 0.5)

      building.mesh.material.emissive = finalColor
      building.mesh.material.emissiveIntensity = 0.1 + (Math.max(building.trafficValue, building.aqiValue) / 100) * 0.2

      const heightScale = 0.8 + (building.trafficValue / 100) * 0.4
      building.targetHeight = building.baseHeight * heightScale

      building.windows.forEach(window => {
        const brightness = 0.3 + Math.random() * 0.7
        window.material.color.setHSL(0.6, 0.8, brightness)
        window.material.opacity = 0.4 + Math.random() * 0.4
      })
    }
  })
}

const animateBuildings = () => {
  buildings.forEach(building => {
    const currentHeight = building.mesh.scale.y
    const targetScale = building.targetHeight / building.baseHeight
    
    building.mesh.scale.y += (targetScale - currentHeight) * 0.03
    
    const newHeight = building.baseHeight * building.mesh.scale.y
    building.mesh.position.y = newHeight / 2
  })
}

const animateRoads = (time) => {
  roads.forEach((road, index) => {
    if (currentData.value) {
      road.trafficFlow = currentData.value.traffic_index / 100
    }

    const intensity = 0.5 + Math.sin(time * 2 + index) * 0.3 * road.trafficFlow
    road.mesh.material.emissive = new THREE.Color(0x0066ff)
    road.mesh.material.emissiveIntensity = intensity * 0.2
  })
}

const animateParticles = (time) => {
  particles.forEach((particle, index) => {
    particle.mesh.position.x += particle.velocity.x
    particle.mesh.position.z += particle.velocity.z

    particle.mesh.position.y = particle.baseY + Math.sin(time * 2 + index) * 0.5

    if (particle.mesh.position.x > 25) particle.mesh.position.x = -25
    if (particle.mesh.position.x < -25) particle.mesh.position.x = 25
    if (particle.mesh.position.z > 25) particle.mesh.position.z = -25
    if (particle.mesh.position.z < -25) particle.mesh.position.z = 25

    const pulse = 0.5 + Math.sin(time * 3 + index * 0.1) * 0.3
    particle.mesh.material.opacity = pulse * 0.6
  })
}

const createRippleEffect = (x, z, color = 0xff3d00) => {
  const rippleGeometry = new THREE.RingGeometry(0.1, 0.5, 32)
  const rippleMaterial = new THREE.MeshBasicMaterial({
    color: color,
    transparent: true,
    opacity: 0.8,
    side: THREE.DoubleSide
  })

  const ripple = new THREE.Mesh(rippleGeometry, rippleMaterial)
  ripple.rotation.x = -Math.PI / 2
  ripple.position.set(x, 0.2, z)
  scene.add(ripple)

  rippleEffects.push({
    mesh: ripple,
    startTime: Date.now(),
    duration: 2000,
    maxRadius: 8
  })
}

const animateRipples = () => {
  const now = Date.now()
  
  rippleEffects = rippleEffects.filter(ripple => {
    const elapsed = now - ripple.startTime
    const progress = elapsed / ripple.duration

    if (progress >= 1) {
      scene.remove(ripple.mesh)
      ripple.mesh.geometry.dispose()
      ripple.mesh.material.dispose()
      return false
    }

    const scale = 1 + progress * (ripple.maxRadius / 0.5)
    ripple.mesh.scale.set(scale, scale, 1)
    ripple.mesh.material.opacity = (1 - progress) * 0.8

    return true
  })
}

const animate = () => {
  animationId = requestAnimationFrame(animate)

  const time = Date.now() * 0.001

  if (autoRotate.value && controls) {
    controls.autoRotate = true
    controls.autoRotateSpeed = 0.5
  } else if (controls) {
    controls.autoRotate = false
  }

  animateBuildings()
  animateRoads(time)
  animateParticles(time)
  animateRipples()

  if (controls) {
    controls.update()
  }

  if (renderer && scene && camera) {
    renderer.render(scene, camera)
  }
}

const onWindowResize = () => {
  if (!container.value || !camera || !renderer) return

  const width = container.value.clientWidth
  const height = container.value.clientHeight

  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

const toggleAutoRotate = () => {
  autoRotate.value = !autoRotate.value
}

const resetCamera = () => {
  if (camera && controls) {
    camera.position.set(25, 20, 25)
    controls.target.set(0, 0, 0)
    controls.update()
  }
}

const loadData = async () => {
  try {
    currentData.value = await dataService.getCurrentData(props.city)
    districtData.value = await dataService.getDistrictData(props.city)
    
    if (anomalyDetector) {
      anomalyDetector.addDataPoint(
        `${props.city}_traffic`,
        currentData.value.traffic_index,
        { city: props.city, type: 'traffic' }
      )
      
      anomalyDetector.addDataPoint(
        `${props.city}_aqi`,
        currentData.value.aqi,
        { city: props.city, type: 'aqi' }
      )

      const anomalies = anomalyDetector.detectAll()
      anomalies.forEach(anomaly => {
        emit('anomaly', anomaly)
        
        if (buildings.length > 0) {
          const randomBuilding = buildings[Math.floor(Math.random() * buildings.length)]
          const color = anomaly.severity === 'error' ? 0xff0000 : 0xffaa00
          createRippleEffect(randomBuilding.position.x, randomBuilding.position.z, color)
        }
      })
    }

    updateBuildingsVisuals()
  } catch (error) {
    console.error('加载数据失败:', error)
  }
}

const cleanup = () => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }

  if (dataUpdateInterval) {
    clearInterval(dataUpdateInterval)
  }

  if (renderer) {
    renderer.dispose()
    if (container.value && renderer.domElement) {
      container.value.removeChild(renderer.domElement)
    }
  }

  window.removeEventListener('resize', onWindowResize)
}

watch(() => props.city, (newCity, oldCity) => {
  if (newCity !== oldCity) {
    cleanup()
    nextTick(() => {
      initScene()
      loadData()
    })
  }
})

onMounted(() => {
  anomalyDetector = new AnomalyDetector({
    windowSize: 10,
    thresholdMultiplier: 2.5
  })

  initScene()
  loadData()
  
  dataUpdateInterval = setInterval(loadData, 5000)
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.city-3d-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.canvas-container {
  width: 100%;
  height: 100%;
}

.info-panel {
  position: absolute;
  top: 20px;
  left: 20px;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 20px;
  color: white;
  min-width: 280px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.info-panel h3 {
  margin: 0 0 15px 0;
  font-size: 1.2rem;
  color: rgba(255, 255, 255, 0.9);
}

.metric-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.metric-row .label {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
  min-width: 90px;
}

.metric-row .value {
  font-size: 1.3rem;
  font-weight: bold;
}

.metric-row .value.good { color: #00c853; }
.metric-row .value.moderate { color: #ffab00; }
.metric-row .value.bad { color: #ff3d00; }
.metric-row .value.aqi-good { color: #00e400; }
.metric-row .value.aqi-moderate { color: #ffff00; }
.metric-row .value.aqi-bad { color: #ff7e00; }
.metric-row .value.aqi-severe { color: #ff0000; }

.metric-row .status {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.5);
}

.controls {
  display: flex;
  gap: 10px;
  margin-top: 15px;
}

.control-btn {
  flex: 1;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.control-btn:hover {
  background: rgba(102, 126, 234, 0.5);
  border-color: #667eea;
}

.legend {
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 15px;
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.legend h4 {
  margin: 0 0 10px 0;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.8);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.7);
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 4px;
}
</style>
