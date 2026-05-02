<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-container">
      <div class="modal-header">
        <h3>⚙️ LLM 配置</h3>
        <button @click="$emit('close')" class="close-btn">×</button>
      </div>
      
      <div class="modal-body">
        <p class="description">
          配置 OpenAI 兼容的 API 接口，用于数据分析和智能建议。
        </p>

        <div class="form-group">
          <label class="form-label">
            <input 
              type="checkbox" 
              v-model="localConfig.enabled"
              class="checkbox-input"
            />
            <span class="label-text">启用 LLM 分析功能</span>
          </label>
        </div>

        <div v-if="localConfig.enabled" class="config-fields">
          <div class="form-group">
            <label class="form-label">API Base URL</label>
            <input 
              type="text" 
              v-model="localConfig.baseUrl"
              placeholder="https://api.openai.com/v1"
              class="form-input"
            />
            <p class="hint">例如: https://api.openai.com/v1 或其他兼容接口地址</p>
          </div>

          <div class="form-group">
            <label class="form-label">API Key</label>
            <div class="input-with-toggle">
              <input 
                :type="showApiKey ? 'text' : 'password'"
                v-model="localConfig.apiKey"
                placeholder="sk-..."
                class="form-input"
              />
              <button 
                type="button"
                @click="showApiKey = !showApiKey"
                class="toggle-btn"
              >
                {{ showApiKey ? '🙈' : '👁️' }}
              </button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Model Name</label>
            <input 
              type="text" 
              v-model="localConfig.modelName"
              placeholder="gpt-3.5-turbo"
              class="form-input"
            />
            <p class="hint">例如: gpt-3.5-turbo, gpt-4, claude-3-opus 等</p>
          </div>

          <div class="test-connection-section">
            <button 
              @click="testConnection"
              :disabled="testingConnection"
              class="test-btn"
            >
              {{ testingConnection ? '🔄 测试中...' : '🔗 测试连接' }}
            </button>
            
            <div v-if="testResult !== null" class="test-result" :class="testResult ? 'success' : 'error'">
              <span v-if="testResult" class="result-icon">✓</span>
              <span v-else class="result-icon">✗</span>
              <span>{{ testResult ? '连接成功！' : '连接失败，请检查配置' }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button @click="$emit('close')" class="btn-secondary">取消</button>
        <button @click="saveConfig" class="btn-primary">保存配置</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { dataService } from '../utils/dataService'

const props = defineProps({
  config: {
    type: Object,
    default: () => ({
      baseUrl: '',
      apiKey: '',
      modelName: 'gpt-3.5-turbo',
      enabled: false
    })
  }
})

const emit = defineEmits(['close', 'save', 'test'])

const showApiKey = ref(false)
const testingConnection = ref(false)
const testResult = ref(null)

const localConfig = reactive({
  baseUrl: props.config.baseUrl || '',
  apiKey: props.config.apiKey || '',
  modelName: props.config.modelName || 'gpt-3.5-turbo',
  enabled: props.config.enabled || false
})

watch(() => props.config, (newConfig) => {
  localConfig.baseUrl = newConfig.baseUrl || ''
  localConfig.apiKey = newConfig.apiKey || ''
  localConfig.modelName = newConfig.modelName || 'gpt-3.5-turbo'
  localConfig.enabled = newConfig.enabled || false
}, { deep: true })

const testConnection = async () => {
  if (!localConfig.baseUrl || !localConfig.apiKey) {
    testResult.value = false
    return
  }

  testingConnection.value = true
  testResult.value = null

  try {
    const result = await dataService.testLLMConnection(localConfig)
    testResult.value = result
  } catch (error) {
    console.error('测试连接失败:', error)
    testResult.value = false
  } finally {
    testingConnection.value = false
  }
}

const saveConfig = () => {
  emit('save', {
    baseUrl: localConfig.baseUrl,
    apiKey: localConfig.apiKey,
    modelName: localConfig.modelName,
    enabled: localConfig.enabled
  })
  emit('close')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(5px);
}

.modal-container {
  width: 90%;
  max-width: 500px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
  animation: modalIn 0.3s ease;
}

@keyframes modalIn {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: rgba(255, 255, 255, 0.9);
}

.close-btn {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.6);
  font-size: 1.5rem;
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.modal-body {
  padding: 25px;
}

.description {
  margin: 0 0 20px 0;
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.5;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 8px;
  cursor: pointer;
}

.checkbox-input {
  width: 18px;
  height: 18px;
  accent-color: #667eea;
  cursor: pointer;
}

.label-text {
  user-select: none;
}

.config-fields {
  padding-top: 15px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.form-input {
  width: 100%;
  padding: 12px 15px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.05);
  color: white;
  font-size: 0.95rem;
  transition: all 0.3s ease;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
  background: rgba(102, 126, 234, 0.1);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
}

.form-input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.hint {
  margin: 5px 0 0 0;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.4);
}

.input-with-toggle {
  display: flex;
  gap: 10px;
}

.input-with-toggle .form-input {
  flex: 1;
}

.toggle-btn {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.05);
  font-size: 1.2rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toggle-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.test-connection-section {
  margin-top: 25px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.test-btn {
  width: 100%;
  padding: 12px 20px;
  border-radius: 8px;
  border: 1px solid rgba(102, 126, 234, 0.5);
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.test-btn:hover:not(:disabled) {
  background: rgba(102, 126, 234, 0.2);
}

.test-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.test-result {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 15px;
  padding: 12px 15px;
  border-radius: 8px;
  font-size: 0.95rem;
}

.test-result.success {
  background: rgba(0, 200, 83, 0.1);
  color: #00c853;
  border: 1px solid rgba(0, 200, 83, 0.3);
}

.test-result.error {
  background: rgba(255, 61, 0, 0.1);
  color: #ff3d00;
  border: 1px solid rgba(255, 61, 0, 0.3);
}

.result-icon {
  font-size: 1.2rem;
  font-weight: bold;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 15px;
  padding: 20px 25px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.2);
}

.btn-secondary, .btn-primary {
  padding: 10px 25px;
  border-radius: 8px;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.15);
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
}
</style>
