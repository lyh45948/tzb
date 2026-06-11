import { useState } from 'react'
import { Wifi, Copy, CheckCircle, AlertCircle } from 'lucide-react'

export default function NfcPage() {
  const [ssid, setSsid] = useState('')
  const [password, setPassword] = useState('')
  const [copied, setCopied] = useState(false)
  const [nfcSupported, setNfcSupported] = useState<boolean | null>(null)

  const handleCopyConfig = () => {
    const config = `WIFI:S:${ssid};T:WPA;P:${password};;`
    navigator.clipboard.writeText(config).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const checkNfcSupport = () => {
    if ('NDEFReader' in window) {
      setNfcSupported(true)
    } else {
      setNfcSupported(false)
    }
  }

  const handleWriteNfc = async () => {
    if (!('NDEFReader' in window)) {
      alert('您的浏览器不支持 Web NFC API')
      return
    }
    try {
      const ndef = new (window as any).NDEFReader()
      await ndef.write(`WIFI:S:${ssid};T:WPA;P:${password};;`)
      alert('WiFi 配置已写入 NFC 标签')
    } catch (e) {
      alert('写入失败: ' + (e as Error).message)
    }
  }

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
        <Wifi className="w-6 h-6 text-sky-600" />
        NFC WiFi配置
      </h2>

      {/* Web NFC 支持检测 */}
      {nfcSupported === null && (
        <button
          onClick={checkNfcSupport}
          className="w-full py-2.5 bg-sky-600 text-white rounded-xl text-sm font-medium hover:bg-sky-700"
        >
          检测 NFC 支持
        </button>
      )}

      {nfcSupported === false && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 flex items-start gap-2">
          <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-yellow-700 font-medium">当前浏览器不支持 Web NFC</p>
            <p className="text-xs text-yellow-600 mt-1">
              Web NFC API 目前仅 Chrome Android 支持。您可以手动复制 WiFi 配置到 NFC 写入工具。
            </p>
          </div>
        </div>
      )}

      {nfcSupported === true && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <span className="text-sm text-green-700">您的浏览器支持 Web NFC</span>
        </div>
      )}

      {/* WiFi 配置表单 */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 space-y-4">
        <h3 className="font-semibold text-gray-700">WiFi 配置</h3>

        <div>
          <label className="text-sm text-gray-500 mb-1 block">WiFi 名称 (SSID)</label>
          <input
            type="text"
            value={ssid}
            onChange={(e) => setSsid(e.target.value)}
            placeholder="输入WiFi名称"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:border-transparent outline-none text-sm"
          />
        </div>

        <div>
          <label className="text-sm text-gray-500 mb-1 block">WiFi 密码</label>
          <input
            type="text"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="输入WiFi密码"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:border-transparent outline-none text-sm"
          />
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="space-y-2">
        {nfcSupported === true && (
          <button
            onClick={handleWriteNfc}
            disabled={!ssid}
            className="w-full flex items-center justify-center gap-2 py-3 bg-sky-600 text-white rounded-xl font-medium hover:bg-sky-700 disabled:opacity-50 transition-colors"
          >
            <Wifi className="w-4 h-4" />
            写入 NFC 标签
          </button>
        )}

        <button
          onClick={handleCopyConfig}
          disabled={!ssid}
          className="w-full flex items-center justify-center gap-2 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 disabled:opacity-50 transition-colors"
        >
          {copied ? (
            <>
              <CheckCircle className="w-4 h-4 text-green-600" />
              已复制
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              复制 WiFi 配置
            </>
          )}
        </button>
      </div>

      {/* 使用说明 */}
      <div className="bg-gray-50 rounded-xl p-4">
        <h4 className="font-medium text-gray-700 mb-2 text-sm">使用说明</h4>
        <ol className="text-xs text-gray-600 space-y-1 list-decimal list-inside">
          <li>输入要配置的 WiFi 名称和密码</li>
          <li>点击"写入 NFC 标签"将配置写入 NFC 标签</li>
          <li>将 NFC 标签靠近 Hi3861 设备的 NFC 感应区</li>
          <li>设备将自动读取 WiFi 配置并连接网络</li>
          <li>如浏览器不支持 NFC，可点击"复制 WiFi 配置"，使用其他 NFC 工具写入</li>
        </ol>
      </div>
    </div>
  )
}
