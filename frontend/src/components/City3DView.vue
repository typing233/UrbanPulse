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
let flowParticles = []
let trailRenderTarget = null
let trailScene = null
let trailCamera = null
let velocityField = null
let rippleEffects = []
let animationId = null
let dataUpdateInterval = null
let anomalyDetector = null
let clock = null

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

const roadFlowVertexShader = `
  varying vec2 vUv;
  varying vec3 vPosition;
  
  void main() {
    vUv = uv;
    vPosition = position;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`

const roadFlowFragmentShader = `
  uniform float time;
  uniform float flowSpeed;
  uniform float trafficIntensity;
  uniform vec3 flowColor;
  uniform float isHorizontal;
  
  varying vec2 vUv;
  varying vec3 vPosition;
  
  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
  }
  
  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
  }
  
  float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    
    for(int i = 0; i < 4; i++) {
      value += amplitude * noise(p * frequency);
      amplitude *= 0.5;
      frequency *= 2.0;
    }
    return value;
  }
  
  void main() {
    vec2 flowCoord;
    if (isHorizontal > 0.5) {
      flowCoord = vec2(vUv.x * 20.0 - time * flowSpeed, vUv.y * 5.0);
    } else {
      flowCoord = vec2(vUv.y * 20.0 - time * flowSpeed, vUv.x * 5.0);
    }
    
    float noise1 = fbm(flowCoord);
    float noise2 = fbm(flowCoord + vec2(100.0));
    
    float flowPattern = noise1 * 0.7 + noise2 * 0.3;
    
    float lines = 0.0;
    float lineSpacing = 0.15;
    float lineWidth = 0.03;
    float linePos = mod(flowCoord.x * 0.5, lineSpacing);
    
    if (linePos < lineWidth) {
      float lineIntensity = smoothstep(lineWidth, 0.0, linePos) * 
                            smoothstep(0.0, lineWidth * 0.3, linePos);
      lines = lineIntensity * (0.5 + flowPattern * 0.5);
    }
    
    float glowLines = 0.0;
    float glowWidth = 0.06;
    if (linePos < glowWidth) {
      glowLines = smoothstep(glowWidth, 0.0, linePos) * 0.5;
    }
    
    float baseRoad = 0.08;
    float finalIntensity = baseRoad + lines * trafficIntensity + glowLines * trafficIntensity * 0.5;
    
    vec3 finalColor = mix(vec3(0.02, 0.02, 0.05), flowColor, finalIntensity);
    
    float alpha = 1.0;
    
    gl_FragColor = vec4(finalColor, alpha);
  }
`

const trailVertexShader = `
  attribute vec3 previous;
  attribute vec3 next;
  attribute float side;
  attribute float width;
  
  uniform float pixelRatio;
  
  varying vec2 vUv;
  varying float vCounters;
  
  void main() {
    vUv = uv;
    vCounters = uv.x;
    
    vec2 aspect = vec2(1.0, 1.0);
    
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    vec4 mvPrevious = modelViewMatrix * vec4(previous, 1.0);
    vec4 mvNext = modelViewMatrix * vec4(next, 1.0);
    
    vec2 currentProj = mvPosition.xy / mvPosition.w;
    vec2 previousProj = mvPrevious.xy / mvPrevious.w;
    vec2 nextProj = mvNext.xy / mvNext.w;
    
    vec2 screen = vec2(
      projectionMatrix[0][0],
      projectionMatrix[1][1]
    );
    
    vec2 dir;
    if (all(equal(position.xy, previous.xy))) {
      dir = normalize(nextProj - currentProj);
    } else if (all(equal(position.xy, next.xy))) {
      dir = normalize(currentProj - previousProj);
    } else {
      vec2 dirA = normalize(currentProj - previousProj);
      vec2 dirB = normalize(nextProj - currentProj);
      dir = normalize(dirA + dirB);
    }
    
    vec2 normal = vec2(-dir.y, dir.x);
    normal *= width * 0.5 * pixelRatio;
    normal.x /= screen.x;
    normal.y /= screen.y;
    
    vec4 offset = vec4(normal * side, 0.0, 0.0);
    gl_Position = mvPosition + offset;
  }
`

const trailFragmentShader = `
  uniform vec3 color;
  uniform float alpha;
  uniform float fadeIn;
  uniform float fadeOut;
  
  varying vec2 vUv;
  varying float vCounters;
  
  void main() {
    float head = smoothstep(0.0, fadeIn, vUv.x);
    float tail = 1.0 - smoothstep(1.0 - fadeOut, 1.0, vUv.x);
    float center = 1.0 - abs(2.0 * vUv.y - 1.0);
    
    float finalAlpha = head * tail * center * alpha;
    
    gl_FragColor = vec4(color, finalAlpha);
  }
`

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

const initVelocityField = () => {
  velocityField = {
    gridSize: 30,
    cellSize: 4,
    velocities: []
  }
  
  for (let z = 0; z < velocityField.gridSize; z++) {
    for (let x = 0; x < velocityField.gridSize; x++) {
      const worldX = (x - velocityField.gridSize / 2) * velocityField.cellSize
      const worldZ = (z - velocityField.gridSize / 2) * velocityField.cellSize
      
      let vx = 0
      let vz = 0
      
      for (let i = -2; i <= 2; i++) {
        const roadZ = i * 12
        const distZ = Math.abs(worldZ - roadZ)
        
        if (distZ < 3) {
          const influence = 1 - distZ / 3
          const direction = i % 2 === 0 ? 1 : -1
          vx += influence * direction * 2
        }
      }
      
      for (let i = -2; i <= 2; i++) {
        const roadX = i * 12
        const distX = Math.abs(worldX - roadX)
        
        if (distX < 3) {
          const influence = 1 - distX / 3
          const direction = i % 2 === 0 ? 1 : -1
          vz += influence * direction * 2
        }
      }
      
      const angle = (x + z) * 0.1
      vx += Math.sin(angle) * 0.5
      vz += Math.cos(angle) * 0.5
      
      velocityField.velocities[z * velocityField.gridSize + x] = { vx, vz }
    }
  }
}

const getVelocityAt = (x, z, time) => {
  if (!velocityField) return { vx: 0, vz: 0 }
  
  const gridX = Math.floor((x / velocityField.cellSize) + velocityField.gridSize / 2)
  const gridZ = Math.floor((z / velocityField.cellSize) + velocityField.gridSize / 2)
  
  const clampedX = Math.max(0, Math.min(velocityField.gridSize - 1, gridX))
  const clampedZ = Math.max(0, Math.min(velocityField.gridSize - 1, gridZ))
  
  const idx = clampedZ * velocityField.gridSize + clampedX
  const baseVel = velocityField.velocities[idx] || { vx: 0, vz: 0 }
  
  const turbulenceX = Math.sin(time * 2 + x * 0.5) * 0.3
  const turbulenceZ = Math.cos(time * 2 + z * 0.5) * 0.3
  
  return {
    vx: baseVel.vx + turbulenceX,
    vz: baseVel.vz + turbulenceZ
  }
}

const createTrailGeometry = (maxLength) => {
  const geometry = new THREE.BufferGeometry()
  const positions = new Float32Array(maxLength * 3 * 2)
  const previous = new Float32Array(maxLength * 3 * 2)
  const next = new Float32Array(maxLength * 3 * 2)
  const side = new Float32Array(maxLength * 2)
  const uv = new Float32Array(maxLength * 2 * 2)
  const indices = []
  
  for (let i = 0; i < maxLength; i++) {
    side[i * 2] = -1
    side[i * 2 + 1] = 1
    
    uv[i * 4] = i / (maxLength - 1)
    uv[i * 4 + 1] = 0
    uv[i * 4 + 2] = i / (maxLength - 1)
    uv[i * 4 + 3] = 1
    
    if (i < maxLength - 1) {
      const a = i * 2
      const b = i * 2 + 1
      const c = i * 2 + 2
      const d = i * 2 + 3
      
      indices.push(a, b, c)
      indices.push(b, d, c)
    }
  }
  
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('previous', new THREE.BufferAttribute(previous, 3))
  geometry.setAttribute('next', new THREE.BufferAttribute(next, 3))
  geometry.setAttribute('side', new THREE.BufferAttribute(side, 1))
  geometry.setAttribute('uv', new THREE.BufferAttribute(uv, 2))
  geometry.setIndex(new THREE.BufferAttribute(new Uint16Array(indices), 1))
  
  geometry.drawRange.count = 0
  
  return geometry
}

const initScene = () => {
  clock = new THREE.Clock()
  
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

  initVelocityField()
  createGround(config)
  createRoads(config)
  createBuildings(config)
  createFlowParticles(config)

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
  roads = []
  
  for (let i = 0; i < 5; i++) {
    const roadMaterial = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        flowSpeed: { value: 1.0 },
        trafficIntensity: { value: 0.5 },
        flowColor: { value: new THREE.Color(0x00aaff) },
        isHorizontal: { value: 1.0 }
      },
      vertexShader: roadFlowVertexShader,
      fragmentShader: roadFlowFragmentShader,
      side: THREE.DoubleSide
    })

    const roadGeometry = new THREE.BoxGeometry(55, 0.15, 2.5)
    const road = new THREE.Mesh(roadGeometry, roadMaterial)
    road.position.set(0, 0.075, (i - 2) * 12)
    road.receiveShadow = true
    scene.add(road)
    
    roads.push({
      mesh: road,
      material: roadMaterial,
      trafficFlow: 0.5,
      baseZ: (i - 2) * 12,
      direction: i % 2 === 0 ? 1 : -1,
      isHorizontal: true
    })

    const roadMaterial2 = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        flowSpeed: { value: 1.0 },
        trafficIntensity: { value: 0.5 },
        flowColor: { value: new THREE.Color(0x00aaff) },
        isHorizontal: { value: 0.0 }
      },
      vertexShader: roadFlowVertexShader,
      fragmentShader: roadFlowFragmentShader,
      side: THREE.DoubleSide
    })

    const roadGeometry2 = new THREE.BoxGeometry(2.5, 0.15, 55)
    const road2 = new THREE.Mesh(roadGeometry2, roadMaterial2)
    road2.position.set((i - 2) * 12, 0.075, 0)
    road2.receiveShadow = true
    scene.add(road2)
    
    roads.push({
      mesh: road2,
      material: roadMaterial2,
      trafficFlow: 0.5,
      baseX: (i - 2) * 12,
      direction: i % 2 === 0 ? 1 : -1,
      isHorizontal: false
    })
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

const createFlowParticles = (config) => {
  flowParticles = []
  
  const particleCount = 300
  const trailLength = 30
  
  for (let i = 0; i < particleCount; i++) {
    const x = (Math.random() - 0.5) * 55
    const z = (Math.random() - 0.5) * 55
    const y = 0.15 + Math.random() * 0.5
    
    const hue = 0.5 + Math.random() * 0.2
    const color = new THREE.Color()
    color.setHSL(hue, 0.8, 0.6)
    
    const trailGeometry = createTrailGeometry(trailLength)
    
    const trailMaterial = new THREE.ShaderMaterial({
      uniforms: {
        color: { value: color },
        alpha: { value: 0.8 },
        fadeIn: { value: 0.1 },
        fadeOut: { value: 0.3 },
        pixelRatio: { value: renderer ? renderer.getPixelRatio() : 1 }
      },
      vertexShader: trailVertexShader,
      fragmentShader: trailFragmentShader,
      transparent: true,
      side: THREE.DoubleSide,
      depthWrite: false
    })
    
    const trail = new THREE.Mesh(trailGeometry, trailMaterial)
    scene.add(trail)
    
    const positions = []
    for (let j = 0; j < trailLength; j++) {
      positions.push(new THREE.Vector3(x, y, z))
    }
    
    flowParticles.push({
      position: new THREE.Vector3(x, y, z),
      velocity: { vx: 0, vz: 0 },
      trail: trail,
      trailGeometry: trailGeometry,
      trailPositions: positions,
      baseY: y,
      color: color,
      size: 0.08 + Math.random() * 0.06,
      speedMultiplier: 0.5 + Math.random() * 0.5
    })
  }
}

const updateTrailGeometry = (particle) => {
  const geometry = particle.trailGeometry
  const positions = geometry.attributes.position.array
  const previous = geometry.attributes.previous.array
  const next = geometry.attributes.next.array
  
  const trailPositions = particle.trailPositions
  const count = trailPositions.length
  
  for (let i = 0; i < count; i++) {
    const pos = trailPositions[i]
    const idx = i * 6
    
    positions[idx] = pos.x
    positions[idx + 1] = pos.y
    positions[idx + 2] = pos.z
    positions[idx + 3] = pos.x
    positions[idx + 4] = pos.y
    positions[idx + 5] = pos.z
    
    const prevIdx = Math.max(0, i - 1)
    const prevPos = trailPositions[prevIdx]
    previous[idx] = prevPos.x
    previous[idx + 1] = prevPos.y
    previous[idx + 2] = prevPos.z
    previous[idx + 3] = prevPos.x
    previous[idx + 4] = prevPos.y
    previous[idx + 5] = prevPos.z
    
    const nextIdx = Math.min(count - 1, i + 1)
    const nextPos = trailPositions[nextIdx]
    next[idx] = nextPos.x
    next[idx + 1] = nextPos.y
    next[idx + 2] = nextPos.z
    next[idx + 3] = nextPos.x
    next[idx + 4] = nextPos.y
    next[idx + 5] = nextPos.z
  }
  
  geometry.attributes.position.needsUpdate = true
  geometry.attributes.previous.needsUpdate = true
  geometry.attributes.next.needsUpdate = true
  geometry.drawRange.count = (count - 1) * 6
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

    const flowSpeed = 0.5 + road.trafficFlow * 2.0
    const trafficColor = getColorForValue(road.trafficFlow * 100, 'traffic')
    
    road.material.uniforms.time.value = time * road.direction
    road.material.uniforms.flowSpeed.value = flowSpeed
    road.material.uniforms.trafficIntensity.value = road.trafficFlow
    road.material.uniforms.flowColor.value = trafficColor
  })
}

const animateFlowParticles = (time, deltaTime) => {
  if (!velocityField) return
  
  const trafficMultiplier = currentData.value ? (0.3 + currentData.value.traffic_index / 100) : 0.8
  
  flowParticles.forEach(particle => {
    const velocity = getVelocityAt(
      particle.position.x, 
      particle.position.z, 
      time
    )
    
    particle.velocity.vx += velocity.vx * deltaTime * 2
    particle.velocity.vz += velocity.vz * deltaTime * 2
    
    const friction = 0.95
    particle.velocity.vx *= friction
    particle.velocity.vz *= friction
    
    const maxSpeed = 3 * trafficMultiplier * particle.speedMultiplier
    const currentSpeed = Math.sqrt(particle.velocity.vx ** 2 + particle.velocity.vz ** 2)
    if (currentSpeed > maxSpeed) {
      const scale = maxSpeed / currentSpeed
      particle.velocity.vx *= scale
      particle.velocity.vz *= scale
    }
    
    particle.position.x += particle.velocity.vx * deltaTime
    particle.position.z += particle.velocity.vz * deltaTime
    
    particle.position.y = particle.baseY + Math.sin(time * 2 + particle.position.x * 0.5) * 0.15
    
    if (particle.position.x > 28) particle.position.x = -28
    if (particle.position.x < -28) particle.position.x = 28
    if (particle.position.z > 28) particle.position.z = -28
    if (particle.position.z < -28) particle.position.z = 28
    
    particle.trailPositions.pop()
    particle.trailPositions.unshift(particle.position.clone())
    
    updateTrailGeometry(particle)
    
    const speed = Math.sqrt(particle.velocity.vx ** 2 + particle.velocity.vz ** 2)
    const speedFactor = Math.min(1, speed / 2)
    particle.trail.material.uniforms.alpha.value = 0.3 + speedFactor * 0.5
    
    const hue = 0.5 + speedFactor * 0.15
    particle.trail.material.uniforms.color.value.setHSL(hue, 0.8, 0.5 + speedFactor * 0.2)
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

  const time = clock.getElapsedTime()
  const deltaTime = clock.getDelta()

  if (autoRotate.value && controls) {
    controls.autoRotate = true
    controls.autoRotateSpeed = 0.5
  } else if (controls) {
    controls.autoRotate = false
  }

  animateBuildings()
  animateRoads(time)
  animateFlowParticles(time, deltaTime)
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
    thresholdMultiplier: 2.5,
    cooldownPeriod: 30000
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
