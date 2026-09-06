import React, { useState, useEffect } from 'react'
import Header from '../components/Header'
import { IoHardwareChip, IoShield, IoTrendingDown, IoCheckmarkCircle, IoWarning, IoShieldCheckmark } from 'react-icons/io5'

const API_URL = '/api'

function FormBadge({ result }) {
  return <span className={`form-badge ${result}`}>{result}</span>
}

function DCUnderCard({ pick, index }) {
  return (
    <div className="card-outer gradient-emerald">
      <div className="card-inner">
        <div className="pick-number" style={{ color: '#10b981' }}>PICK {index + 1}</div>
        <div className="league-name">{pick.match?.league}</div>
        
        <div className="teams-container">
          <span className="team-name">{pick.match?.home}</span>
          <span className="vs-text">VS</span>
          <span className="team-name">{pick.match?.away}</span>
        </div>
        
        <div className="markets-container">
          <div className="market-row">
            <span className="market-label">DC:</span>
            <span className="market-selection">{pick.dc_selection}</span>
            <span className="market-odds">{pick.dc_odds?.toFixed(2)}</span>
          </div>
          <div className="market-row">
            <span className="market-label">GOALS:</span>
            <span className="market-selection">{pick.under_selection}</span>
            <span className="market-odds">{pick.under_odds?.toFixed(2)}</span>
          </div>
        </div>
        
        <div className="combined-row" style={{ borderColor: '#10b981' }}>
          <span className="combined-label">COMBINED</span>
          <span className="combined-odds" style={{ color: '#10b981' }}>{pick.combined_odds?.toFixed(2)}</span>
        </div>
        
        <div className="section-label">FORM (LAST 5)</div>
        <div className="form-container">
          <div className="form-row">
            {pick.home_form?.split('').map((r, i) => <FormBadge key={`h${i}`} result={r} />)}
          </div>
          <div className="form-row">
            {pick.away_form?.split('').map((r, i) => <FormBadge key={`a${i}`} result={r} />)}
          </div>
        </div>
        
        <div className="confidence-row">
          <span className="confidence-label">CONFIDENCE</span>
          <span className="confidence-value">{pick.combined_confidence}%</span>
        </div>
        <div className="progress-bg">
          <div className="progress-fill" style={{ width: `${pick.combined_confidence}%`, background: '#10b981' }} />
        </div>
      </div>
    </div>
  )
}

function DCUnderPage() {
  const [picks, setPicks] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchPicks()
  }, [])

  const fetchPicks = async () => {
    try {
      const response = await fetch(`${API_URL}/dc-under`)
      const data = await response.json()
      setPicks(data.dc_under_picks || [])
    } catch (error) {
      console.error('Error fetching DC Under:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <div className="loading-text">Loading DC & Under 4.5...</div>
      </div>
    )
  }

  return (
    <div className="page-content">
      <Header />
      
      <div className="market-header" style={{ color: '#10b981' }}>
        DC & UNDER 4.5 GOALS
      </div>
      
      <div className="cards-grid">
        <div className="cards-row">
          {picks.slice(0, 2).map((pick, i) => <DCUnderCard key={pick.id} pick={pick} index={i} />)}
        </div>
        <div className="cards-row">
          {picks.slice(2, 4).map((pick, i) => <DCUnderCard key={pick.id} pick={pick} index={i + 2} />)}
        </div>
      </div>
      
      <div className="bottom-section">
        <div className="bottom-row">
          <div className="market-focus-box" style={{ borderColor: '#10b981' }}>
            <div className="mf-label">MARKET FOCUS</div>
            <div className="mf-value">Double Chance + Under 4.5</div>
          </div>
          <div className="tagline-box">
            <span className="tagline-main">SAFE & DEFENSIVE</span>
            <IoShieldCheckmark style={{ color: '#10b981', fontSize: '14px' }} />
          </div>
        </div>
        
        <div className="features-row">
          <div className="feature-item">
            <IoHardwareChip className="feature-icon" style={{ color: '#10b981' }} />
            <span className="feature-title">AI POWERED</span>
          </div>
          <div className="feature-item">
            <IoShield className="feature-icon" style={{ color: '#10b981' }} />
            <span className="feature-title">LOW RISK</span>
          </div>
          <div className="feature-item">
            <IoTrendingDown className="feature-icon" style={{ color: '#10b981' }} />
            <span className="feature-title">DEFENSIVE</span>
          </div>
          <div className="feature-item">
            <IoCheckmarkCircle className="feature-icon" style={{ color: '#22c55e' }} />
            <span className="feature-title">4 SINGLES</span>
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

export default DCUnderPage
