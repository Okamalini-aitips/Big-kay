import React, { useState, useEffect } from 'react'

const API_URL = '/api'

const RANGES = [
  { label: '7 Days', days: 7 },
  { label: '14 Days', days: 14 },
  { label: '30 Days', days: 30 },
  { label: 'All Time', days: 0 },
]

function hrClass(hr) {
  if (hr == null) return ''
  if (hr >= 60) return 'hr-good'
  if (hr >= 50) return 'hr-mid'
  return 'hr-bad'
}

function AdminResultsPage() {
  const [key, setKey] = useState(localStorage.getItem('okamoney_admin_key') || '')
  const [authed, setAuthed] = useState(false)
  const [days, setDays] = useState(30)
  const [stats, setStats] = useState(null)
  const [settleDate, setSettleDate] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() - 1)
    return d.toISOString().slice(0, 10)
  })
  const [pending, setPending] = useState([])
  const [selections, setSelections] = useState({})
  const [msg, setMsg] = useState('')

  const loadStats = async (k = key, d = days) => {
    const r = await fetch(`${API_URL}/admin/results/stats?key=${encodeURIComponent(k)}&days=${d}`)
    if (r.status === 403) { setMsg('Invalid admin key'); setAuthed(false); return false }
    setStats(await r.json()); setAuthed(true); setMsg(''); return true
  }

  const loadPending = async (k = key, date = settleDate) => {
    const r = await fetch(`${API_URL}/admin/results/pending?key=${encodeURIComponent(k)}&date=${date}`)
    if (r.ok) { const d = await r.json(); setPending(d.tips || []) }
  }

  const handleLogin = async () => {
    const ok = await loadStats()
    if (ok) { localStorage.setItem('okamoney_admin_key', key); loadPending() }
  }

  useEffect(() => { if (key) handleLogin() }, [])
  useEffect(() => { if (authed) loadStats(key, days) }, [days])

  const settleOne = (pickId, result) => setSelections(s => ({ ...s, [pickId]: result }))

  const submitSettle = async () => {
    if (Object.keys(selections).length === 0) { setMsg('Mark some tips first'); return }
    const r = await fetch(`${API_URL}/admin/results/settle?key=${encodeURIComponent(key)}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date: settleDate, results: selections }),
    })
    const d = await r.json()
    setMsg(`Settled ${d.updated} tips`); setSelections({}); loadPending(); loadStats()
  }

  const simulate = async () => {
    if (!window.confirm('DEMO ONLY: auto-grade this day by probability? Use only for testing.')) return
    const r = await fetch(`${API_URL}/admin/results/simulate?key=${encodeURIComponent(key)}&date=${settleDate}`, { method: 'POST' })
    const d = await r.json()
    setMsg(`Simulated ${d.graded} results (demo)`); loadPending(); loadStats()
  }

  if (!authed) {
    return (
      <div className="admin-results">
        <h2>Admin Results & Analytics</h2>
        <p>Enter admin key to view performance analytics.</p>
        <input className="search-input" style={{ maxWidth: 320 }} type="password"
          placeholder="Admin key" value={key} onChange={e => setKey(e.target.value)} />
        <div className="admin-actions">
          <button className="btn-primary" onClick={handleLogin}>Unlock</button>
        </div>
        {msg && <p style={{ color: '#dc2626' }}>{msg}</p>}
      </div>
    )
  }

  return (
    <div className="admin-results">
      <h2>Results & Analytics</h2>

      <div className="range-tabs">
        {RANGES.map(r => (
          <button key={r.days} className={`range-tab ${days === r.days ? 'active' : ''}`}
            onClick={() => setDays(r.days)}>{r.label}</button>
        ))}
      </div>

      {stats && (
        <>
          <div className="stat-cards">
            <div className="stat-card"><div className="v">{stats.hit_rate ?? 0}%</div><div className="l">Hit Rate</div></div>
            <div className="stat-card"><div className="v">{stats.won || 0}/{stats.settled || 0}</div><div className="l">Won/Settled</div></div>
            <div className="stat-card"><div className="v">{stats.roi ?? 0}%</div><div className="l">ROI</div></div>
            <div className="stat-card"><div className="v">{stats.total_picks || 0}</div><div className="l">Total Picks</div></div>
          </div>

          <h3>By Market</h3>
          <table className="market-table">
            <thead><tr><th>Market</th><th>Hit Rate</th><th>Won</th><th>Total</th><th>Avg Odds</th><th>ROI</th></tr></thead>
            <tbody>
              {Object.entries(stats.by_market || {})
                .sort((a, b) => (b[1].hit_rate || 0) - (a[1].hit_rate || 0))
                .map(([mkt, v]) => (
                  <tr key={mkt}>
                    <td>{mkt}</td>
                    <td className={hrClass(v.hit_rate)}>{v.hit_rate}%</td>
                    <td>{v.won}</td>
                    <td>{v.total}</td>
                    <td>{v.avg_odds}</td>
                    <td className={hrClass(v.roi >= 0 ? 60 : 40)}>{v.roi}%</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </>
      )}

      <h3 style={{ marginTop: 24 }}>Settle a Day</h3>
      <div className="admin-actions">
        <input className="search-input" style={{ maxWidth: 180 }} type="date"
          value={settleDate} onChange={e => setSettleDate(e.target.value)} />
        <button className="btn-primary" onClick={() => loadPending()}>Load</button>
        <button className="btn-primary" onClick={submitSettle}>Save Results</button>
        <button className="btn-demo" onClick={simulate}>Simulate (demo)</button>
      </div>
      {msg && <p style={{ color: '#166534' }}>{msg}</p>}

      <div style={{ background: '#fff', borderRadius: 10, padding: 12 }}>
        {pending.length === 0 && <p>No tips loaded for this date.</p>}
        {pending.map(t => (
          <div key={t.pick_id} className="settle-row">
            <span className="sel">
              <strong>{t.home} v {t.away}</strong> — {t.selection} @ {Number(t.odds).toFixed(2)}
              {t.result !== 'pending' && <em style={{ marginLeft: 6, color: '#777' }}>({t.result})</em>}
            </span>
            {['won', 'lost', 'void'].map(r => (
              <button key={r}
                className={`settle-btn ${r} ${(selections[t.pick_id] || t.result) === r ? 'active' : ''}`}
                onClick={() => settleOne(t.pick_id, r)}>{r}</button>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export default AdminResultsPage
