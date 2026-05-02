export class AnomalyDetector {
  constructor(options = {}) {
    this.windowSize = options.windowSize || 10
    this.thresholdMultiplier = options.thresholdMultiplier || 2.5
    this.cooldownPeriod = options.cooldownPeriod || 30000
    this.history = new Map()
    this.lastAnomalyTime = new Map()
  }

  addDataPoint(key, value, metadata = {}) {
    if (!this.history.has(key)) {
      this.history.set(key, [])
    }
    
    const data = this.history.get(key)
    data.push({ value, timestamp: Date.now(), metadata })
    
    if (data.length > this.windowSize) {
      data.shift()
    }
  }

  isInCooldown(key) {
    const lastTime = this.lastAnomalyTime.get(key)
    if (!lastTime) return false
    return Date.now() - lastTime < this.cooldownPeriod
  }

  detect(key) {
    if (this.isInCooldown(key)) {
      return null
    }

    const data = this.history.get(key)
    if (!data || data.length < this.windowSize) {
      return null
    }

    const values = data.map(d => d.value)
    const mean = this.calculateMean(values)
    const stdDev = this.calculateStdDev(values, mean)
    const currentValue = values[values.length - 1]
    
    const deviation = Math.abs(currentValue - mean)
    const zScore = deviation / (stdDev || 1)

    if (zScore > this.thresholdMultiplier) {
      this.lastAnomalyTime.set(key, Date.now())
      
      return {
        key,
        value: currentValue,
        mean,
        stdDev,
        zScore,
        severity: zScore > 3.5 ? 'error' : 'warning',
        metadata: data[data.length - 1].metadata,
        message: `检测到异常波动: 当前值 ${currentValue.toFixed(1)} 超出正常范围 (均值: ${mean.toFixed(1)}, 标准差: ${stdDev.toFixed(1)})`
      }
    }

    return null
  }

  calculateMean(values) {
    return values.reduce((sum, v) => sum + v, 0) / values.length
  }

  calculateStdDev(values, mean) {
    const squaredDiffs = values.map(v => Math.pow(v - mean, 2))
    return Math.sqrt(squaredDiffs.reduce((sum, v) => sum + v, 0) / values.length)
  }

  detectAll() {
    const anomalies = []
    for (const key of this.history.keys()) {
      const anomaly = this.detect(key)
      if (anomaly) {
        anomalies.push(anomaly)
      }
    }
    return anomalies
  }

  clear() {
    this.history.clear()
    this.lastAnomalyTime.clear()
  }
}

export default AnomalyDetector
