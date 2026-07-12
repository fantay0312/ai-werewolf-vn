import { useState, useEffect } from 'react'
import { configApi, type LLMConfigResponse, type LLMTestResponse } from '../../api'
import { cn } from '../../lib/utils'

interface SettingsModalProps {
  isVisible: boolean
  onClose: () => void
  onSaved: () => void
}

export function SettingsModal({ isVisible, onClose, onSaved }: SettingsModalProps) {
  const selectArrowStyle = {
    backgroundImage: "url('data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%228%22 height=%228%22%3E%3Cpath d=%22M0 2l4 4 4-4%22 fill=%22none%22 stroke=%22%23666%22 stroke-width=%221%22/%3E%3C/svg%3E')"
  }

  const [config, setConfig] = useState<LLMConfigResponse>({
    api_key_set: false,
    api_base: null,
    model: 'gpt-3.5-turbo',
    max_tokens: 1000,
    temperature: 0.7
  })

  const [formData, setFormData] = useState({
    api_key: '',
    api_base: '',
    model: 'gpt-3.5-turbo',
    max_tokens: 1000,
    temperature: 0.7
  })

  const [customModel, setCustomModel] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<LLMTestResponse | null>(null)
  const [fetchingModels, setFetchingModels] = useState(false)
  const [fetchModelsError, setFetchModelsError] = useState('')
  const [remoteModels, setRemoteModels] = useState<Array<{ id: string; owned_by: string }>>([])

  useEffect(() => {
    async function loadConfig() {
      try {
        const data = await configApi.getLLMConfig()
        setConfig(data)
        setFormData({
          api_key: '',
          api_base: data.api_base || '',
          model: data.model,
          max_tokens: data.max_tokens,
          temperature: data.temperature
        })
      } catch (error) {
        console.error('加载配置失败:', error)
      }
    }

    if (isVisible) {
      loadConfig()
      setTestResult(null)
    }
  }, [isVisible])

  async function handleSave() {
    setSaving(true)
    setTestResult(null)

    try {
      const updateData: Record<string, unknown> = {
        api_base: formData.api_base || null,
        model: formData.model === 'custom' ? customModel : formData.model,
        max_tokens: formData.max_tokens,
        temperature: formData.temperature
      }

      if (formData.api_key) {
        updateData.api_key = formData.api_key
      }

      const result = await configApi.setLLMConfig(updateData)
      setConfig(result)
      setFormData(prev => ({ ...prev, api_key: '' }))

      onSaved()
      onClose()
    } catch (error) {
      console.error('保存配置失败:', error)
      setTestResult({
        success: false,
        message: '保存配置失败'
      })
    } finally {
      setSaving(false)
    }
  }

  async function handleTest() {
    setTesting(true)
    setTestResult(null)

    try {
      const updateData: Record<string, unknown> = {
        api_base: formData.api_base || null,
        model: formData.model === 'custom' ? customModel : formData.model
      }

      if (formData.api_key) {
        updateData.api_key = formData.api_key
      }

      await configApi.setLLMConfig(updateData)
      const res = await configApi.testLLMConnection()
      setTestResult(res)
    } catch (error) {
      setTestResult({
        success: false,
        message: '测试失败: ' + (error as Error).message
      })
    } finally {
      setTesting(false)
    }
  }

  async function handleFetchModels() {
    setFetchingModels(true)
    setFetchModelsError('')
    setRemoteModels([])

    try {
      const updateData: Record<string, unknown> = {
        api_base: formData.api_base || null,
      }
      if (formData.api_key) {
        updateData.api_key = formData.api_key
      }
      await configApi.setLLMConfig(updateData)

      const result = await configApi.fetchModels()
      if (result.success && result.models && result.models.length > 0) {
        setRemoteModels(result.models)
      } else {
        setFetchModelsError(result.message || '未获取到模型')
      }
    } catch (error) {
      setFetchModelsError('请求失败: ' + (error as Error).message)
    } finally {
      setFetchingModels(false)
    }
  }

  if (!isVisible) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center font-['VT323',monospace] antialiased">
      <div className="absolute inset-0 bg-black/85" onClick={onClose}></div>
      
      <div className="relative w-full max-w-[520px] mx-4 bg-black border border-[#333] animate-slide-in-up">
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#222] bg-[#0a0a0a]">
          <span className="text-[13px] text-[#555] tracking-[1px]">┌─ SYS.CONFIG // LLM_INTERFACE ─┐</span>
          <button className="font-['VT323',monospace] text-[14px] bg-transparent border-none text-[#555] cursor-pointer px-1.5 py-0.5 tracking-[1px] hover:text-white hover:bg-[#333]" onClick={onClose}>[X]</button>
        </div>

        <div className="p-4 max-h-[420px] overflow-y-auto flex flex-col gap-3.5 scrollbar-thin scrollbar-thumb-[#333] scrollbar-track-black">
          
          <div className="flex flex-col gap-1">
            <label className="text-[14px] text-[#888] tracking-[1px]">API_BASE_URL:</label>
            <input
              value={formData.api_base}
              onChange={e => setFormData({ ...formData, api_base: e.target.value })}
              type="text"
              className="font-['VT323',monospace] text-[16px] px-2.5 py-1.5 bg-[#0a0a0a] border border-[#333] text-white outline-none tracking-[0.5px] focus:border-[#666] placeholder:text-[#333]"
              placeholder="https://api.openai.com/v1"
            />
            <p className="text-[12px] text-[#333] tracking-[0.5px]">// 留空使用默认地址</p>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[14px] text-[#888] tracking-[1px]">API_KEY:</label>
            <div className="flex gap-1.5">
              <input
                value={formData.api_key}
                onChange={e => setFormData({ ...formData, api_key: e.target.value })}
                type={showApiKey ? 'text' : 'password'}
                className="flex-1 font-['VT323',monospace] text-[16px] px-2.5 py-1.5 bg-[#0a0a0a] border border-[#333] text-white outline-none tracking-[0.5px] focus:border-[#666] placeholder:text-[#333]"
                placeholder={config.api_key_set ? '******** (SET)' : '未设置'}
              />
              <button
                type="button"
                className="font-['VT323',monospace] text-[14px] px-3 py-1.5 bg-[#111] border border-[#333] text-[#666] cursor-pointer tracking-[1px] hover:text-white hover:border-[#555]"
                onClick={() => setShowApiKey(!showApiKey)}
              >
                {showApiKey ? 'HIDE' : 'SHOW'}
              </button>
            </div>
            <p className="text-[12px] tracking-[0.5px]">
              {config.api_key_set ? <span className="text-[#0a0]">// STATUS: CONFIGURED</span> : <span className="text-[#664400]">// STATUS: NOT SET (FALLBACK MODE)</span>}
            </p>
          </div>

          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <label className="text-[14px] text-[#888] tracking-[1px]">MODEL:</label>
              <button
                type="button"
                className="font-['VT323',monospace] text-[12px] px-2.5 py-0.5 bg-[#111] border border-[#333] text-[#666] cursor-pointer tracking-[1px] hover:text-white hover:border-[#555] disabled:opacity-40 disabled:cursor-not-allowed"
                onClick={handleFetchModels}
                disabled={fetchingModels}
              >
                {fetchingModels ? 'LOADING...' : '> FETCH_MODELS'}
              </button>
            </div>

            {remoteModels.length > 0 ? (
              <div className="flex flex-col gap-1.5 mt-1">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] text-[#333] tracking-[0.5px]">// {remoteModels.length} MODELS AVAILABLE</span>
                  <button type="button" className="font-['VT323',monospace] text-[12px] px-2 py-0.5 bg-[#111] border border-[#333] text-[#666] cursor-pointer hover:text-white hover:border-[#555]" onClick={() => setRemoteModels([])}>CLEAR</button>
                </div>
                <div className="max-h-[180px] overflow-y-auto flex flex-col gap-0.5 border border-[#222] bg-[#050505] p-1 scrollbar-thin scrollbar-thumb-[#333]">
                  {remoteModels.map(m => (
                    <button
                      key={m.id}
                      type="button"
                      className={cn("flex items-center justify-between px-2.5 py-1 bg-transparent border border-transparent font-['VT323',monospace] text-[14px] text-[#888] cursor-pointer text-left transition-all hover:bg-[#111] hover:text-[#ccc]", formData.model === m.id && "bg-[#1a1a1a] border-[#555] text-white")}
                      onClick={() => setFormData({ ...formData, model: m.id })}
                    >
                      <span className="flex-1 overflow-hidden text-ellipsis whitespace-nowrap">{m.id}</span>
                      <span className="text-[11px] text-[#444] ml-3 shrink-0">{m.owned_by}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div>
                <select 
                  value={formData.model} 
                  onChange={e => setFormData({ ...formData, model: e.target.value })} 
                style={selectArrowStyle}
                className="w-full font-['VT323',monospace] text-[16px] px-2.5 py-1.5 bg-[#0a0a0a] border border-[#333] text-white outline-none tracking-[0.5px] cursor-pointer appearance-none bg-no-repeat bg-[right_10px_center] pr-7"
                >
                  <option value="gpt-3.5-turbo" className="bg-[#111] text-white">gpt-3.5-turbo</option>
                  <option value="gpt-4" className="bg-[#111] text-white">gpt-4</option>
                  <option value="gpt-4-turbo" className="bg-[#111] text-white">gpt-4-turbo</option>
                  <option value="gpt-4o" className="bg-[#111] text-white">gpt-4o</option>
                  <option value="gpt-4o-mini" className="bg-[#111] text-white">gpt-4o-mini</option>
                  <option value="claude-3-opus" className="bg-[#111] text-white">claude-3-opus</option>
                  <option value="claude-3-sonnet" className="bg-[#111] text-white">claude-3-sonnet</option>
                  <option value="claude-3-haiku" className="bg-[#111] text-white">claude-3-haiku</option>
                  <option value="deepseek-chat" className="bg-[#111] text-white">deepseek-chat</option>
                  <option value="custom" className="bg-[#111] text-white">custom...</option>
                </select>
                {formData.model === 'custom' && (
                  <input
                    value={customModel}
                    onChange={e => setCustomModel(e.target.value)}
                    type="text"
                    className="w-full mt-1.5 font-['VT323',monospace] text-[16px] px-2.5 py-1.5 bg-[#0a0a0a] border border-[#333] text-white outline-none tracking-[0.5px] focus:border-[#666] placeholder:text-[#333]"
                    placeholder="输入自定义模型名称"
                  />
                )}
              </div>
            )}

            {formData.model && formData.model !== 'custom' && (
              <p className="text-[12px] text-[#333] tracking-[0.5px]">// SELECTED: {formData.model}</p>
            )}
            {fetchModelsError && (
              <p className="text-[12px] text-[#a83a3a] tracking-[0.5px]">// {fetchModelsError}</p>
            )}
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[14px] text-[#888] tracking-[1px]">TEMPERATURE: {formData.temperature}</label>
            <input
              value={formData.temperature}
              onChange={e => setFormData({ ...formData, temperature: Number(e.target.value) })}
              type="range"
              min="0"
              max="2"
              step="0.1"
              className="w-full h-0.5 bg-[#333] appearance-none cursor-pointer my-1 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:cursor-pointer [&::-moz-range-thumb]:w-3 [&::-moz-range-thumb]:h-3 [&::-moz-range-thumb]:bg-white [&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:border-none"
            />
            <p className="text-[12px] text-[#333] tracking-[0.5px]">// 0=确定性 &lt;─&gt; 2=随机性</p>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[14px] text-[#888] tracking-[1px]">MAX_TOKENS:</label>
            <input
              value={formData.max_tokens}
              onChange={e => setFormData({ ...formData, max_tokens: Number(e.target.value) })}
              type="number"
              min="100"
              max="8000"
              className="font-['VT323',monospace] text-[16px] px-2.5 py-1.5 bg-[#0a0a0a] border border-[#333] text-white outline-none tracking-[0.5px] focus:border-[#666]"
            />
          </div>

          {testResult && (
            <div className={cn("px-3 py-2 border text-[14px] tracking-[0.5px]", testResult.success ? "border-[#0a0] text-[#0a0]" : "border-[#a00] text-[#a00]")}>
              <span>{testResult.success ? '[OK]' : '[ERR]'} {testResult.message}</span>
              {testResult.response && (
                <p className="text-[12px] text-[#333] tracking-[0.5px] mt-1">&gt; {testResult.response}</p>
              )}
            </div>
          )}

        </div>

        <div className="flex items-center justify-between px-4 py-2.5 border-t border-[#222] bg-[#0a0a0a]">
          <button
            className="font-['VT323',monospace] text-[14px] px-3.5 py-1.5 bg-transparent border border-[#333] text-[#888] cursor-pointer tracking-[1px] transition-all hover:text-white hover:border-[#555] hover:bg-[#111] disabled:opacity-40 disabled:cursor-not-allowed"
            onClick={handleTest}
            disabled={testing}
          >
            {testing ? 'TESTING...' : '> TEST_CONN'}
          </button>
          <div className="flex gap-1.5">
            <button className="font-['VT323',monospace] text-[14px] px-3.5 py-1.5 bg-transparent border border-[#333] text-[#888] cursor-pointer tracking-[1px] transition-all hover:text-white hover:border-[#555] hover:bg-[#111]" onClick={onClose}>&gt; CANCEL</button>
            <button
              className="font-['VT323',monospace] text-[14px] px-3.5 py-1.5 bg-transparent border border-[#555] text-white cursor-pointer tracking-[1px] transition-all hover:bg-white hover:text-black disabled:opacity-40 disabled:cursor-not-allowed"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'SAVING...' : '> SAVE'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
