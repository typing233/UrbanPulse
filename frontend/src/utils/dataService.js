import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:5001/api',
  timeout: 10000
})

export const dataService = {
  async getCurrentData(city) {
    const response = await api.get(`/current/${encodeURIComponent(city)}`)
    return response.data
  },

  async getDistrictData(city, date) {
    const response = await api.get(`/district/${encodeURIComponent(city)}`, {
      params: { date: date ? date.toISOString().split('T')[0] : undefined }
    })
    return response.data
  },

  async getHistoricalData(city, days = 30) {
    const response = await api.get(`/historical/${encodeURIComponent(city)}`, {
      params: { days }
    })
    return response.data
  },

  async getHourlyData(city, date) {
    const response = await api.get(`/hourly/${encodeURIComponent(city)}`, {
      params: { date: date ? date.toISOString().split('T')[0] : undefined }
    })
    return response.data
  },

  async getCities() {
    const response = await api.get('/cities')
    return response.data
  },

  async testLLMConnection(config) {
    const response = await api.post('/llm/test', {
      base_url: config.baseUrl,
      api_key: config.apiKey,
      model_name: config.modelName
    })
    return response.data.success
  },

  async getLLMAnalysis(config, data) {
    const response = await api.post('/llm/analyze', {
      config: {
        base_url: config.baseUrl,
        api_key: config.apiKey,
        model_name: config.modelName,
        enabled: config.enabled
      },
      data
    })
    return response.data
  }
}

export default dataService
