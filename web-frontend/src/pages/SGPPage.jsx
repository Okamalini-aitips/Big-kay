import React, { useState, useEffect } from 'react'
import Header from '../components/Header'
import { IoCheckmarkCircle, IoHardwareChip, IoAnalytics, IoTrendingUp, IoWarning } from 'react-icons/io5'

const API_URL = '/api'

function FormBadge({ result }) {
  return <span className={`form-badge ${result}`}>{result}</span>
}

function SGPCard({ sgp }) {
  const getGradient = (name) => {
    if (name.includes('Safe Bet 1') || name.includes('Safe Bet 2')) return 'gradient-green'
    if (name.includes('Value')) return 'gradient-orange'
    return 'gradient-red'
  }

  const getColor = (name) => {
    if (name.includes('Safe Bet 1') || name.includes('Safe Bet 2')) return '#22c55e'
    if (name.includes('Value')) return '#f59e0b'
    return '#ef4444'
  }

  const gradient = getGradient(sgp.ticket_name)
  const color = getColor(sgp.ticket_name)

  return (
    <div className={`card-outer ${gradient}`}>
      <div className="card-inner">
        <div className="ticket-header">
          <span className="ticket-label" style={{ color }}>{sgp.ticket_name?.toUpperCase()}</span>
          <span className="odds-range">({sgp.odds_bracket})</span>
        </div>
        
        <div className="league-name">{sgp.match?.league}</div>
        
        <div className="teams-container">
          <span className="team-name">{sgp.match?.home}</span>
          <span className="vs-text">VS</span>
          <span className="team-name">{sgp.match?.away}</span>
        </div>
        
        <div className="legs-container">
          {sgp.legs?.map((leg, i) => (
            <div key={i} className="leg-row">
              <IoCheckmarkCircle className="leg-check" />
              <span className="leg-selection">{leg.selection}</span>
              <span className="leg-odds">{leg.odds?.toFixed(2)}</span>
            </div>
          ))}
        </div>
        
        <div className="combined-row" style={{ borderColor: color }}>
          <span className="combined-label">COMBINED</span>
          <span className="combined-odds" style={{ color }}>{sgp.combined_odds?.toFixed(2)}</span>
        </div>
        
        <div className="section-label">FORM (LAST 5)</div>
        <div className="form-container">
          <div className="form-row">
            {sgp.home_form?.split('').map((r, i) => <FormBadge key={`h${i}`} result={r} />)}
          </div>
          <div className="form-row">
            {sgp.away_form?.split('').map((r, i) => <FormBadge key={`a${i}`} result={r} />)}
          </div>
        </div>
        
        <div className="confidence-row">
          <span className="confidence-label">CONFIDENCE</span>
          <span className="confidence-value">{sgp.combined_confidence}%</span>
        </div>
        <div className="progress-bg">
          <div className="progress-fill" style={{ width: `${sgp.combined_confidence}%`, background: '#22c55e' }} />
        </div>
      </div>
    </div>
  )
}

function SGPPage() {
  const [picks, setPicks] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchPicks()
  }, [])

  const fetchPicks = async () => {
    try {
      const response = await fetch(`${API_URL}/sgp`)
      const data = await response.json()
      setPicks(data.sgp_picks || [])
    } catch (error) {
      console.error('Error fetching SGP:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <div className="loading-text">Loading SGP tickets...</div>
      </div>
    )
  }

  return (
    <div className="page-content">
      <Header />
      
      <div className="market-header" style={{ color: '#f59e0b' }}>
        SAME GAME PARLAY - BUILD A BET
      </div>
      
      <div className="cards-grid">
        <div className="cards-row">
          {picks.slice(0, 2).map((sgp) => <SGPCard key={sgp.id} sgp={sgp} />)}
        </div>
        <div className="cards-row">
          {picks.slice(2, 4).map((sgp) => <SGPCard key={sgp.id} sgp={sgp} />)}
        </div>
      </div>
      
      <div className="bottom-section">
        <div className="legend-row">
          <div className="legend-item" style={{ borderLeftColor: '#22c55e' }}>
            <div className="legend-label">SAFE</div>
            <div className="legend-odds">1.90-3.00</div>
          </div>
          <div className="legend-item" style={{ borderLeftColor: '#f59e0b' }}>
            <div className="legend-label">VALUE</div>
            <div className="legend-odds">3.01-4.00</div>
          </div>
          <div className="legend-item" style={{ borderLeftColor: '#ef4444' }}>
            <div className="legend-label">HIGH</div>
            <div className="legend-odds">4.01-7.00</div>
          </div>
        </div>
        
        <div className="bottom-row">
          <div className="market-focus-box" style={{ borderColor: '#f59e0b' }}>
            <div className="mf-label">12 MARKET POOL</div>
            <div className="mf-value">Goals • Corners • Cards</div>
          </div>
          <div className="tagline-box">
            <span className="tagline-main">BET SMART. WIN MORE.</span>
            <IoCheckmarkCircle style={{ color: '#22c55e', fontSize: '14px' }} />
          </div>
        </div>
        
        <div className="features-row">
          <div className="feature-item">
            <IoHardwareChip className="feature-icon" style={{ color: '#f59e0b' }} />
            <span className="feature-title">AI POWERED</span>
          </div>
          <div className="feature-item">
            <IoAnalytics className="feature-icon" style={{ color: '#f59e0b' }} />
            <span className="feature-title">2-4 LEGS</span>
          </div>
          <div className="feature-item">
            <IoTrendingUp className="feature-icon" style={{ color: '#f59e0b' }} />
            <span className="feature-title">4 TICKETS</span>
          </div>
          <div className="feature-item">
            <IoCheckmarkCircle className="feature-icon" style={{ color: '#22c55e' }} />
            <span className="feature-title">SAME GAME</span>
          </div>
        </div>
        
        <div className="powered-by">POWERED BY AI. DRIVEN BY DATA. DELIVERING RESULTS.</div>
        <div className="brand-sig">OkaMoney AI Tips ✓</div>
        
        <div className="disclaimer">
          <IoWarning className="disclaimer-icon" />
          <span className="disclaimer-text">
            Disclaimer: OkaMoney AI Tips provides predictions for informational purposes only. Predictions are probability based not guaranteed wins. Please gamble responsibly.
          </span>
        </div>
      </div>
    </div>
  )
}

export default SGPPage
