import { useState, useEffect } from 'react'
import { Link } from 'react-router'
import { getApiUrl } from '@/repository'
import Navbar from '@/components/Navbar'

type ClientToken = {
  clientId?: string
  token?: string
}

type ClientTokens = Record<string, ClientToken>

const decodeJwtPayload = (token?: string): Record<string, any> | null => {
  if (!token) return null
  const parts = token.split('.')
  if (parts.length < 2) return null

  try {
    const padded = parts[1].padEnd(parts[1].length + ((4 - parts[1].length % 4) % 4), '=')
    const decoded = atob(padded.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded)
  } catch {
    return null
  }
}

const getTokenExpiry = (token?: string): Date | null => {
  const payload = decodeJwtPayload(token)
  if (!payload) return null

  const raw =
    payload.exp ??
    payload.Exp ??
    payload.expiration ??
    payload.expiry ??
    payload.exp_time ??
    payload.expDate

  if (raw === undefined || raw === null) return null

  if (typeof raw === 'number') return new Date(raw * 1000)

  const numeric = Number(raw)
  if (!Number.isNaN(numeric) && Number.isFinite(numeric)) {
    return new Date(numeric * 1000)
  }

  const parsed = new Date(raw)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

const formatExpiryLabel = (token?: string) => {
  const expiry = getTokenExpiry(token)
  if (!expiry) return { label: 'Expires: unknown', isExpired: false }

  const isExpired = expiry.getTime() <= Date.now()
  const dateLabel = expiry.toLocaleString()
  return {
    label: `Expires: ${dateLabel}${isExpired ? ' (expired)' : ''}`,
    isExpired,
  }
}

const formatTimestamp = (timestamp?: string | null): string | null => {
  if (!timestamp) return null
  const match = timestamp.match(/(\d{4})(\d{2})(\d{2})[_ ]?(\d{2})(\d{2})(\d{2})/)
  if (!match) return timestamp
  const [, year, month, day, hour, minute, second] = match
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`
}

export default function TokensPage() {
  const [baseToken, setBaseToken] = useState('')
  const [originalToken, setOriginalToken] = useState('')
  const [clientTokens, setClientTokens] = useState<ClientTokens>({})
  const [timestamp, setTimestamp] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    loadTokens()
  }, [])

  const loadTokens = async () => {
    try {
      setLoading(true)
      const apiUrl = getApiUrl()

      // Load base token
      const baseTokenResponse = await fetch(`${apiUrl}/tokens/base`, {
        credentials: 'include',
      })
      const baseTokenData = await baseTokenResponse.json()
      setBaseToken(baseTokenData.base_token || '')
      setOriginalToken(baseTokenData.base_token || '')

      // Load client tokens
      const clientTokensResponse = await fetch(`${apiUrl}/tokens/client`, {
        credentials: 'include',
      })
      const clientTokensData = await clientTokensResponse.json()
      setClientTokens(clientTokensData.tokens || {})
      setTimestamp(clientTokensData.timestamp)
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to load tokens: ${error}` })
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async (value?: string) => {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      setMessage({ type: 'success', text: 'Token copied to clipboard' })
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to copy: ${error}` })
    }
  }

  const handleSaveBaseToken = async () => {
    try {
      setLoading(true)
      setMessage(null)
      const apiUrl = getApiUrl()

      const response = await fetch(`${apiUrl}/tokens/base`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ base_token: baseToken }),
      })

      if (!response.ok) {
        throw new Error('Failed to update base token')
      }

      setOriginalToken(baseToken)
      setMessage({ type: 'success', text: 'Base token updated successfully!' })
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to update base token: ${error}` })
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateTokens = async () => {
    try {
      setGenerating(true)
      setMessage(null)
      const apiUrl = getApiUrl()

      const response = await fetch(`${apiUrl}/tokens/generate`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ base_token: baseToken }),
      })

      const data = await response.json()

      if (!response.ok || !data.success) {
        throw new Error(data.message || 'Failed to generate tokens')
      }

      setMessage({
        type: 'success',
        text: `${data.message}. Refresh the page to see updated client tokens.`,
      })

      // Reload client tokens after generation
      setTimeout(() => {
        loadTokens()
      }, 1000)
    } catch (error: any) {
      setMessage({ type: 'error', text: `Failed to generate tokens: ${error.message || error}` })
    } finally {
      setGenerating(false)
    }
  }

  const hasChanges = baseToken !== originalToken
  const baseTokenExpiry = formatExpiryLabel(baseToken)
  const formattedTimestamp = formatTimestamp(timestamp)

  return (
    <div className="text-gray-300 antialiased h-screen flex flex-col overflow-hidden font-sans bg-[#0a0e17]">
      <Navbar>
        <div className="flex flex-col gap-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex flex-col min-w-0">
              <h1 className="text-2xl font-bold text-white tracking-tight truncate flex items-center gap-3">
                API Token Management
              </h1>
              <p className="text-gray-500 truncate mt-1">
                {formattedTimestamp
                  ? `Last generated ${formattedTimestamp}`
                  : 'No tokens generated yet'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap text-sm text-gray-400">
            <Link to="/" className="hover:text-neon-400 transition-colors">Home</Link>
            <span className="text-gray-600">/</span>
            <span>Settings</span>
            <span className="text-gray-600">/</span>
            <span className="text-gray-200">API Tokens</span>
          </div>
        </div>
      </Navbar>

      <main className="flex-1 overflow-y-auto custom-scrollbar p-6 max-w-5xl mx-auto w-full relative z-10 space-y-6">
        {/* Message Banner */}
        {message && (
          <div
            className={`p-4 rounded-xl border backdrop-blur-md ${
              message.type === 'success'
                ? 'bg-green-500/10 border-green-500/20 text-green-400'
                : 'bg-red-500/10 border-red-500/20 text-red-400'
            }`}
          >
            {message.text}
          </div>
        )}

        {/* Base Token Section */}
        <div className="glass-panel rounded-2xl p-6 space-y-6 shadow-glass">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight mb-1">Base Token</h2>
              <p className="text-sm text-gray-500">
                Master token used to generate client-specific tokens.
              </p>
            </div>
            <div className="text-xs text-right flex flex-col items-end gap-1">
              <span className="text-gray-500">
                {baseToken ? `${baseToken.length} chars` : 'Not set'}
              </span>
              {baseToken && (
                <span
                  className={`font-semibold ${
                    baseTokenExpiry.isExpired ? 'text-red-400' : 'text-neon-400'
                  }`}
                >
                  {baseTokenExpiry.label}
                </span>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest">Base Token (JWT)</label>
            <textarea
              value={baseToken}
              onChange={(e) => setBaseToken(e.target.value)}
              className="w-full bg-dark-950/50 border border-gray-800 rounded-xl px-4 py-3 text-gray-300 placeholder-gray-600 focus:outline-none focus:border-neon-500/50 focus:ring-1 focus:ring-neon-500/50 transition-all font-mono text-xs min-h-[160px] custom-scrollbar resize-y"
              placeholder="Paste your base JWT token here..."
            />
          </div>

          <div className="flex flex-wrap gap-3 pt-2">
            <button
              onClick={handleSaveBaseToken}
              disabled={loading || !hasChanges}
              className={`px-4 py-2 rounded-lg font-medium transition-all shadow-lg ${
                hasChanges && !loading
                  ? 'bg-neon-600 hover:bg-neon-500 text-white shadow-neon/20 hover:shadow-neon/40'
                  : 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700'
              }`}
            >
              {loading ? 'Saving...' : 'Save Base Token'}
            </button>

            <button
              onClick={handleGenerateTokens}
              disabled={generating || !baseToken}
              className={`px-4 py-2 rounded-lg font-medium transition-all shadow-lg ${
                baseToken && !generating
                  ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-500/20 hover:shadow-indigo-500/40'
                  : 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700'
              }`}
            >
              {generating ? 'Generating...' : 'Generate Client Tokens'}
            </button>

            <button
              type="button"
              onClick={() => handleCopy(baseToken)}
              disabled={!baseToken}
              className={`px-4 py-2 rounded-lg text-sm font-medium border transition-all ${
                baseToken
                  ? 'border-gray-700 text-gray-300 hover:bg-white/5 hover:text-white'
                  : 'border-gray-800 text-gray-600 cursor-not-allowed'
              }`}
            >
              Copy Base Token
            </button>
          </div>
        </div>

        {/* Client Tokens Section */}
        <div className="glass-panel rounded-2xl p-6 shadow-glass">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-bold text-white tracking-tight">Client Tokens</h2>
            {formattedTimestamp && (
              <span className="text-xs font-mono text-gray-500">
                Generated: {formattedTimestamp}
              </span>
            )}
          </div>

          {Object.keys(clientTokens).length === 0 ? (
            <div className="text-center py-12 border border-dashed border-gray-800 rounded-xl bg-dark-950/30">
              <p className="text-gray-500">
                No client tokens generated yet. Click "Generate Client Tokens" above to create them.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {Object.entries(clientTokens).map(([siteName, data]) => {
                const { label: expiryLabel, isExpired } = formatExpiryLabel(data.token)
                return (
                  <div
                    key={siteName}
                    className="border border-white/5 rounded-xl p-5 flex flex-col gap-4 bg-white/5 hover:bg-white/10 transition-colors"
                  >
                    <div className="flex justify-between items-start gap-3">
                      <div>
                        <h3 className="font-bold text-white text-lg mb-1">{siteName}</h3>
                        <div className="flex items-center gap-2 text-xs">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full border ${
                              isExpired
                                ? 'bg-red-500/10 border-red-500/20 text-red-400'
                                : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                            }`}
                          >
                            {isExpired ? 'Expired' : 'Active'}
                          </span>
                          <span
                            className={`font-mono ${
                              isExpired ? 'text-red-400' : 'text-gray-400'
                            }`}
                          >
                            {expiryLabel}
                          </span>
                        </div>
                      </div>
                      <div className="text-xs text-gray-500 font-mono text-right break-all max-w-[200px]">
                        ID: {data.clientId || '—'}
                      </div>
                    </div>
                    
                    <div className="bg-dark-950/50 p-3 rounded-lg border border-black/20 flex items-center gap-3 group">
                      <code className="text-xs break-all text-gray-400 flex-1 font-mono leading-relaxed">
                        {data.token?.slice(0, 140)}...
                      </code>
                      <button
                        type="button"
                        onClick={() => handleCopy(data.token)}
                        className="px-3 py-1.5 text-xs font-medium bg-neon-500/10 text-neon-400 rounded hover:bg-neon-500/20 transition-colors opacity-0 group-hover:opacity-100"
                      >
                        Copy
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
