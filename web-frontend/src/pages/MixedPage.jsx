import React, { useState, useEffect } from 'react'
import Header from '../components/Header'
import { IoHardwareChip, IoGitBranch, IoTrendingUp, IoStar, IoWarning, IoLayers } from 'react-icons/io5'

const API_URL = '/api'

function MixedCard({ parlay }) {
  const getGradient = (name) => {
    if (name.includes('1')) return 'gradient-green'
    if (name.includes('2')) return 'gradient-blue'
    if (name.includes('3')) return 'gradient-purple'
    return 'gradient-orange'
  }

  const getColor = (name) => {
    if (name.includes('1')) return '#22c55e'
    if (name.includes('2')) return '#3b82f6'
    if (name.includes('3')) return '#8b5cf6'
    return '#f97316'
  }

  const gradient = getGradient(parlay.ticket_name)
  const color = getColor(parlay.ticket_name)

  return (
    <div className={`card-outer ${gradient}`}>
      <div className="card-inner">
        <div className="ticket-header">
          <span className="ticket-label" style={{ color }}>{parlay.ticket_name?.toUpperCase()}</span>
          <span className="odds-range">({parlay.odds_bracket})</span>
        </div>
        
        <div className="games-count">{parlay.num_games} GAMES</div>
        
        <div className="legs-container">
          {parlay.legs?.map((leg, i) => (
            <div key={i} className="mixed-leg-row">
              <div className="leg-match-info">
                <div className="leg-teams">{leg.home} vs {leg.away}</div>
                <div className="leg-league">{leg.league}</div>
              </div>
              <div className="leg-market-info">
                <span className="leg-selection">{leg.selection}</span>
                <span className="leg-odds" style={{ color: '#f59e0b' }}>{leg.odds?.toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>
        
        <div className="combined-row" style={{ borderColor: color }}>
          <span className="combined-label">COMBINED ODDS</span>
          <span className="combined-odds" style={{ color }}>{parlay.combined_odds?.toFixed(2)}</span>
        </div>
        
        <div className="confidence-row">
          <span className="confidence-label">CONFIDENCE</span>
          <span className="confidence-value">{parlay.combined_confidence}%</span>
        </div>
        <div className="progress-bg">
          <div className="progress-fill" style={{ width: `${parlay.combined_confidence}%`, background: color }} />
        </div>
      </div>
    </div>
  )
}

function MixedPage() {
  const [parlays, setParlays] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchParlays()
  }, [])

  const fetchParlays = async () => {
    try {
      const response = await fetch(`${API_URL}/mixed-parlay`)
      const data = await response.json()
      setParlays(data.mixed_parlays || [])
    } catch (error) {
      console.error('Error fetching Mixed Parlays:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <div className="loading-text">Loading Mixed Parlays...</div>
      </div>
    )
  }

  return (
    <div className="page-content">
      <Header />
      
      <div className="market-header" style={{ color: '#3b82f6' }}>
        MIXED GAMES PARLAY
      </div>
      
      <div className="cards-grid">
        <div className="cards-row">
          {parlays.slice(0, 2).map((parlay) => <MixedCard key={parlay.id} parlay={parlay} />)}
        </div>
        <div className="cards-row">
          {parlays.slice(2, 4).map((parlay) => <MixedCard key={parlay.id} parlay={parlay} />)}
        </div>
      </div>
      
      <div className="bottom-section">
        <div className="legend-row">
          <div className="legend-item" style={{ borderLeftColor: '#22c55e' }}>
            <div className="legend-label">MP 1</div>
            <div className="legend-odds">3.50-5.00</div>
          </div>
          <div className="legend-item" style={{ borderLeftColor: '#3b82f6' }}>
            <div className="legend-label">MP 2</div>
            <div className="legend-odds">5.01-6.50</div>
          </div>
          <div className="legend-item" style={{ borderLeftColor: '#8b5cf6' }}>
            <div className="legend-label">MP 3</div>
            <div className="legend-odds">6.51-8.00</div>
          </div>
          <div className="legend-item" style={{ borderLeftColor: '#f97316' }}>
            <div className="legend-label">MP 4</div>
            <div className="legend-odds">8.01-12.00</div>
          </div>
        </div>
        
        <div className="bottom-row">
          <div className="market-focus-box" style={{ borderColor: '#3b82f6' }}>
            <div className="mf-label">12 MARKET POOL</div>
            <div className="mf-value">3-5 Different Games</div>
          </div>
          <div className="tagline-box">
            <span className="tagline-main">MULTI-GAME VALUE</span>
            <IoLayers style={{ color: '#3b82f6', fontSize: '14px' }} />
          </div>
        </div>
        
        <div className="features-row">
          <div className="feature-item">
            <IoHardwareChip className="feature-icon" style={{ color: '#3b82f6' }} />
            <span className="feature-title">AI POWERED</span>
          </div>
          <div className="feature-item">
            <IoGitBranch className="feature-icon" style={{ color: '#3b82f6' }} />
            <span className="feature-title">MULTI-GAME</span>
          </div>
          <div className="feature-item">
            <IoTrendingUp className="feature-icon" style={{ color: '#3b82f6' }} />
            <span className="feature-title">4 TICKETS</span>
          </div>
          <div className="feature-item">
            <IoStar className="feature-icon" style={{ color: '#f59e0b' }} />
            <span className="feature-title">BEST MARKETS</span>
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

export default MixedPage
