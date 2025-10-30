"use client"

import { useState, useEffect } from "react"
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts"

type VizSpec = {
  type: "line" | "bar" | "table"
  x?: "date" | "category" | "region" | "store" | "store_name" | "store_id" | "sku"
  y?: string[]
  groupBy?: ("date" | "region" | "category" | "store" | "store_name" | "store_id" | "sku")[]
  aggregation?: "sum" | "avg" | "count"
  explanations?: string[]
}

type ChatResponse = {
  answer: string
  sql?: string
  viz?: VizSpec
  rows?: any[]
  schema?: { name: string; type: string }[]
}

type Turn = {
  user: string
  assistant?: ChatResponse
}

export default function Page() {
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [turns, setTurns] = useState<Turn[]>([])

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

  async function onSend() {
    if (!input.trim()) return
    const question = input
    setInput("")
    setLoading(true)
    setError(null)
    setTurns((t) => [...t, { user: question }])
    try {
      const r = await fetch(`${backendUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question }),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const data: ChatResponse = await r.json()
      setTurns((t) => {
        const copy = [...t]
        copy[copy.length - 1] = { user: question, assistant: data }
        return copy
      })
    } catch (e: any) {
      setError(e.message)
      setTurns((t) => {
        const copy = [...t]
        copy[copy.length - 1] = { user: question, assistant: { answer: `Error: ${e.message}` } }
        return copy
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-100">
      <div className="mx-auto max-w-6xl px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-2">
            <div className="text-4xl font-extrabold text-[#DA291C] tracking-tight">CVS</div>
            <div className="h-10 w-px bg-gradient-to-b from-transparent via-gray-400 to-transparent"></div>
            <h1 className="text-3xl font-bold text-gray-800">Analytics</h1>
          </div>
          <p className="text-gray-600 mt-2">Ask questions about your retail sales data</p>
        </div>

        {/* Input Card */}
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6 mb-6">
          <div className="flex gap-3">
          <input
            className="flex-1 border-2 border-gray-200 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-[#DA291C] focus:border-[#DA291C] transition-all text-gray-700 placeholder-gray-400"
            placeholder="Ask a question about retail_sales..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" ? onSend() : undefined}
            disabled={loading}
          />
          <button className="px-6 py-3 bg-gradient-to-r from-[#DA291C] to-[#B82218] hover:from-[#B82218] hover:to-[#9A1C15] text-white rounded-lg disabled:opacity-50 transition-all flex items-center gap-2 shadow-md hover:shadow-lg font-medium" onClick={onSend} disabled={loading}>
            {loading ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Sending...
              </>
            ) : (
              "Send"
            )}
          </button>
        </div>
        {error && (
          <div className="mt-4 p-3 bg-red-50 border-l-4 border-red-500 text-red-700 rounded">
            {error}
          </div>
        )}
        </div>

        {/* Chat History - Modern Chat Interface */}
        <div className="space-y-3 max-h-[calc(100vh-280px)] overflow-y-auto pr-2">
          {turns.length === 0 && (
            <div className="text-center py-16 text-gray-400">
              <div className="text-6xl mb-4">📊</div>
              <p className="text-xl font-medium text-gray-600">Start analyzing your retail sales data</p>
              <p className="text-sm mt-2 text-gray-500">Try: "What are the top 3 categories by net sales each month?"</p>
            </div>
          )}
          {turns.map((t, idx) => (
            <ChatMessage key={idx} idx={idx} turn={t} />
          ))}
        </div>
      </div>
    </main>
  )
}

// Modern chat message component
function ChatMessage({ idx, turn }: { idx: number; turn: Turn }) {
  const [showDetails, setShowDetails] = useState(false)
  const [showFullscreen, setShowFullscreen] = useState(false)
  const viz = turn.assistant?.viz
  const sql = turn.assistant?.sql
  const rows = turn.assistant?.rows || []

  return (
    <>
      {/* User Question - Right aligned */}
      <div className="flex justify-end">
        <div className="max-w-3xl w-full flex gap-3 justify-end">
          <div className="flex-1"></div>
          <div className="bg-gradient-to-r from-[#DA291C] to-[#B82218] text-white rounded-2xl rounded-tr-sm px-5 py-3 shadow-md max-w-[85%]">
            <p className="text-sm font-medium leading-relaxed">{turn.user}</p>
          </div>
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center text-gray-600 font-semibold text-xs">
            You
          </div>
        </div>
      </div>

      {/* AI Response - Left aligned */}
      <div className="flex justify-start">
        <div className="max-w-3xl w-full flex gap-3">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-[#DA291C] to-[#B82218] flex items-center justify-center text-white font-bold text-xs">
            AI
          </div>
          <div className="flex-1 bg-white rounded-2xl rounded-tl-sm shadow-md border border-gray-200 overflow-hidden">
            {/* Answer text */}
            <div className="px-5 py-4 border-b border-gray-100">
              <p className="text-gray-700 leading-relaxed">{turn.assistant?.answer || "Processing..."}</p>
            </div>

            {/* Visualization/Results */}
            {(viz || sql) && (
              <div className="p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-[#DA291C] animate-pulse"></div>
                    <span className="font-semibold text-gray-800 text-sm">Analysis Results</span>
                  </div>
                  <div className="flex gap-3">
                    {viz && (
                      <button 
                        className="text-xs text-[#DA291C] hover:text-[#B82218] font-medium transition-colors flex items-center gap-1 px-2 py-1 hover:bg-red-50 rounded"
                        onClick={() => setShowFullscreen(true)}
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                        </svg>
                        Full Screen
                      </button>
                    )}
                    <button 
                      className="text-xs text-gray-600 hover:text-[#DA291C] font-medium transition-colors px-2 py-1 hover:bg-gray-50 rounded"
                      onClick={() => setShowDetails((s) => !s)}
                    >
                      {showDetails ? "Hide" : "Show"} SQL
                    </button>
                  </div>
                </div>
                
                {viz ? (
                  <>
                    <ChartOrTable viz={viz} rows={rows} />
                    {showFullscreen && (
                      <FullscreenChart viz={viz} rows={rows} onClose={() => setShowFullscreen(false)} />
                    )}
                  </>
                ) : sql ? (
                  <div className="bg-gray-50 rounded-lg p-3 text-xs">
                    <div className="font-mono bg-white p-2 rounded border text-gray-700">{sql}</div>
                  </div>
                ) : null}
                
                {showDetails && sql && (
                  <div className="mt-4 border-t border-gray-200 pt-4">
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="font-medium text-gray-800 mb-2 text-xs">Technical Details</div>
                      <pre className="text-xs overflow-auto bg-white p-2 rounded border font-mono text-gray-700 max-h-60">
                        <code>{JSON.stringify({ sql, viz, rowsCount: rows.length }, null, 2)}</code>
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

function pickXKey(viz: VizSpec, rows: any[]): string | null {
  // Prefer an explicit groupBy dimension like sku/region/category/store if present in rows
  const candidates = [...(viz.groupBy || []), viz.x]
  for (const key of candidates) {
    if (rows.length && key in rows[0]) return key
  }
  // Fallback: first string-like field
  const first = rows.length ? Object.keys(rows[0]).find(k => typeof rows[0][k] === "string") : null
  return first || (rows.length ? Object.keys(rows[0])[0] : null)
}

function ChartOrTable({ viz, rows }: { viz: VizSpec; rows: any[] }) {
  if (viz.type === "table") {
    if (!rows?.length) return (
      <div className="text-sm text-gray-500 bg-gray-50 rounded-lg p-4 text-center">No rows returned.</div>
    )
    const cols = Object.keys(rows[0] || {})
    return (
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gradient-to-r from-gray-50 to-gray-100">
              <tr>
                {cols.map((c) => (
                  <th key={c} className="text-left font-semibold text-gray-700 px-4 py-3 border-b border-gray-200">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.slice(0, 50).map((r, i) => (
                <tr key={i} className="hover:bg-gray-50 transition-colors">
                  {cols.map((c) => (
                    <td key={c} className="px-4 py-3 text-gray-700">{String(r[c])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  const yKey = viz.y?.[0]
  const xKey = pickXKey(viz, rows)
  
  // Find the actual y key in the data - handle cases where yKey might be different (e.g., "total_net_sales" vs "net_sales")
  let actualYKey = yKey
  if (rows.length > 0 && yKey) {
    // If yKey doesn't exist, try to find it (case-insensitive or with variations)
    if (!(yKey in rows[0])) {
      const foundKey = Object.keys(rows[0]).find(k => 
        k.toLowerCase().includes(yKey.toLowerCase()) || 
        yKey.toLowerCase().includes(k.toLowerCase()) ||
        k.toLowerCase().replace(/_/g, '') === yKey.toLowerCase().replace(/_/g, '')
      )
      if (foundKey) actualYKey = foundKey
    }
  }
  
  const data = (rows && rows.length && actualYKey && xKey)
    ? rows
        .map((r) => {
          const xVal = r[xKey]
          const yVal = r[actualYKey!]
          // Convert to number if possible, otherwise use as string
          const yNum = typeof yVal === 'string' && !isNaN(Number(yVal)) ? Number(yVal) : 
                       typeof yVal === 'number' ? yVal : 
                       yVal
          return { x: xVal ?? 'Unknown', y: yNum ?? 0 }
        })
        .filter(d => d.y !== undefined && d.y !== null && !isNaN(d.y))
    : []

  if (!data.length) {
    return <div className="text-sm text-gray-600 bg-gray-50 rounded-lg p-4">No valid data points found. Available keys: {rows.length > 0 ? Object.keys(rows[0]).join(', ') : 'none'}</div>
  }

  const TopList = () => {
    const displayYKey = actualYKey || yKey
    return (
      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <div className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
          <svg className="w-4 h-4 text-[#DA291C]" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M3.293 9.707a1 1 0 010-1.414l6-6a1 1 0 011.414 0l6 6a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L4.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
          </svg>
          Top Results
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {rows.slice(0, 10).map((r, i) => {
            const xVal = xKey ? (r[xKey] ?? 'N/A') : 'N/A'
            const yVal = displayYKey ? (r[displayYKey] ?? 'N/A') : 'N/A'
            return (
              <div key={i} className="flex items-center justify-between bg-white rounded-lg px-3 py-2 border border-gray-200 hover:border-[#DA291C] transition-colors">
                <span className="text-gray-600 text-sm">{i + 1}.</span>
                <span className="flex-1 text-gray-800 font-medium ml-2 truncate">{String(xVal)}</span>
                <span className="text-[#DA291C] font-semibold ml-2">{String(yVal)}</span>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  if (viz.type === "line") {
    return (
      <>
        <div className="bg-gradient-to-br from-white to-gray-50 rounded-lg p-4 border border-gray-200 mb-4">
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 60 }}>
                <XAxis 
                  dataKey="x" 
                  interval="preserveStartEnd" 
                  angle={-45} 
                  height={80} 
                  tick={{ fontSize: 11, fill: '#666' }}
                  stroke="#999"
                />
                <YAxis 
                  tick={{ fontSize: 11, fill: '#666' }}
                  stroke="#999"
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                    border: '1px solid #DA291C',
                    borderRadius: '8px',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                  }}
                />
                <Legend wrapperStyle={{ paddingTop: '10px' }} />
                <Line 
                  type="monotone" 
                  dataKey="y" 
                  stroke="#DA291C" 
                  strokeWidth={3} 
                  dot={{ fill: '#DA291C', strokeWidth: 2, r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <TopList />
      </>
    )
  }

  return (
    <>
      <div className="bg-gradient-to-br from-white to-gray-50 rounded-lg p-4 border border-gray-200 mb-4">
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 60 }}>
              <XAxis 
                dataKey="x" 
                interval="preserveStartEnd" 
                angle={-45} 
                height={80} 
                tick={{ fontSize: 11, fill: '#666' }}
                stroke="#999"
              />
              <YAxis 
                tick={{ fontSize: 11, fill: '#666' }}
                stroke="#999"
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(255, 255, 255, 0.95)', 
                  border: '1px solid #DA291C',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                }}
              />
              <Legend wrapperStyle={{ paddingTop: '10px' }} />
              <Bar 
                dataKey="y" 
                fill="#DA291C"
                radius={[8, 8, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <TopList />
    </>
  )
}

function FullscreenChart({ viz, rows, onClose }: { viz: VizSpec; rows: any[]; onClose: () => void }) {
  const yKey = viz.y?.[0]
  const xKey = pickXKey(viz, rows)
  
  // Find the actual y key in the data - handle cases where yKey might be different
  let actualYKey = yKey
  if (rows.length > 0 && yKey) {
    if (!(yKey in rows[0])) {
      const foundKey = Object.keys(rows[0]).find(k => 
        k.toLowerCase().includes(yKey.toLowerCase()) || 
        yKey.toLowerCase().includes(k.toLowerCase()) ||
        k.toLowerCase().replace(/_/g, '') === yKey.toLowerCase().replace(/_/g, '')
      )
      if (foundKey) actualYKey = foundKey
    }
  }
  
  const data = (rows && rows.length && actualYKey && xKey)
    ? rows
        .map((r) => {
          const xVal = r[xKey]
          const yVal = r[actualYKey!]
          const yNum = typeof yVal === 'string' && !isNaN(Number(yVal)) ? Number(yVal) : 
                       typeof yVal === 'number' ? yVal : 
                       yVal
          return { x: xVal ?? 'Unknown', y: yNum ?? 0 }
        })
        .filter(d => d.y !== undefined && d.y !== null && !isNaN(d.y))
    : []

  // Close on ESC key
  useEffect(() => {
    const handleEsc = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose()
      }
    }
    window.addEventListener("keydown", handleEsc)
    return () => window.removeEventListener("keydown", handleEsc)
  }, [onClose])

  if (!data.length) {
    return null
  }

  const TopList = () => {
    const displayYKey = actualYKey || yKey
    return (
      <div className="mt-6 max-w-5xl mx-auto">
        <div className="font-semibold text-gray-800 mb-4 text-lg">Top Results</div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {rows.slice(0, 20).map((r, i) => {
            const xVal = xKey ? (r[xKey] ?? 'N/A') : 'N/A'
            const yVal = displayYKey ? (r[displayYKey] ?? 'N/A') : 'N/A'
            return (
              <div key={i} className="bg-white rounded-lg px-4 py-3 border border-gray-200 hover:border-[#DA291C] hover:shadow-md transition-all">
                <div className="text-xs text-gray-500 mb-1">#{i + 1}</div>
                <div className="font-semibold text-gray-800 text-sm mb-1 truncate">{String(xVal)}</div>
                <div className="text-[#DA291C] font-bold">{String(yVal)}</div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-90 z-50 flex flex-col items-center justify-center p-4" onClick={onClose}>
      <div className="w-full h-full max-w-7xl flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-white text-xl font-semibold">Full Screen Chart</h2>
          <button
            onClick={onClose}
            className="text-white hover:text-gray-300 px-4 py-2 bg-[#DA291C] hover:bg-[#B82218] rounded transition-colors"
          >
            Close (ESC)
          </button>
        </div>
        <div className="flex-1 min-h-0 bg-white rounded-lg p-6 overflow-auto">
          {viz.type === "line" ? (
            <>
              <div className="h-[calc(100vh-300px)] min-h-[500px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 100 }}>
                    <XAxis dataKey="x" angle={-45} textAnchor="end" height={120} tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="y" stroke="#DA291C" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <TopList />
            </>
          ) : (
            <>
              <div className="h-[calc(100vh-300px)] min-h-[500px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 100 }}>
                    <XAxis dataKey="x" angle={-45} textAnchor="end" height={120} tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="y" fill="#DA291C" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <TopList />
            </>
          )}
        </div>
      </div>
    </div>
  )
}

