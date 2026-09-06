import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import Header from '../components/Header'
import { IoLockClosed, IoCheckmarkCircle, IoHardwareChip, IoFlame, IoTrendingUp, IoWarning, IoRocket, IoShield } from 'react-icons/io5'

const API_URL = '/api'

function FormBadge({ result }) {
  return <span className={`form-badge ${result}`}>{result}</span>
}

// ==========================================
// BUILD A BET (SGP) CARD COMPONENT
// ==========================================
function SGPCard({ ticket, index }) {
  const gradientClass = ticket.ticket_name?.includes('Safe') ? 'gradient-gold' 
    : ticket.ticket_name?.includes('Value') ? 'gradient-blue'
    : 'gradient-red'
  
  // Generate mock league positions for display
  const homePos = Math.floor(Math.random() * 8) + 1
  const awayPos = Math.floor(Math.random() * 10) + 4
  
  return (
    <div className={`card-outer ${gradientClass}`}>
      <div className="card-inner">
        <div className="ticket-name">{ticket.ticket_name}</div>
        <div className="odds-bracket">{ticket.odds_bracket}</div>
        <div className="league-name">{ticket.match?.league}</div>
        
        <div className="teams-container">
          <span className="team-name">{ticket.match?.home}</span>
          <span className="vs-text">VS</span>
          <span className="team-name">{ticket.match?.away}</span>
        </div>
        
        <div className="legs-container">
          {ticket.legs?.map((leg, i) => (
            <div key={i} className="leg-row">
              <span className="leg-market">{leg.market}</span>
              <span className="leg-selection">{leg.selection}</span>
              <span className="leg-odds">{leg.odds?.toFixed(2)}</span>
            </div>
          ))}
        </div>
        
        <div className="combined-row">
          <span className="combined-label">COMBINED</span>
          <span className="combined-odds">{ticket.combined_odds?.toFixed(2)}</span>
        </div>
        
        {/* League Position instead of Form */}
        <div className="section-label">LEAGUE POSITION</div>
        <div className="league-pos-mini">
          <div className="pos-row">
            <span className="pos-team">{ticket.match?.home?.substring(0, 10)}</span>
            <span className="pos-badge-mini">{homePos}</span>
          </div>
          <div className="pos-row">
            <span className="pos-team">{ticket.match?.away?.substring(0, 10)}</span>
            <span className="pos-badge-mini">{awayPos}</span>
          </div>
        </div>
        
        <div className="confidence-row">
          <span className="confidence-label">CONFIDENCE</span>
          <span className="confidence-value">{ticket.combined_confidence}%</span>
        </div>
        <div className="progress-bg">
          <div className="progress-fill" style={{ width: `${ticket.combined_confidence}%` }} />
        </div>
      </div>
    </div>
  )
}

// ==========================================
// MIXED PARLAY CARD COMPONENT
// ==========================================

// Helper function to format selection with market type
function formatSelectionWithMarket(selection, market) {
  const selLower = selection?.toLowerCase() || ''
  const marketLower = market?.toLowerCase() || ''
  
  // If selection already includes market type, return as-is
  if (selLower.includes('goal') || selLower.includes('corner') || selLower.includes('card') || 
      selLower.includes('btts') || selLower.includes('win') || selLower.includes('1x') || 
      selLower.includes('x2') || selLower.includes('12')) {
    return selection
  }
  
  // Add market type based on selection pattern
  if (selLower.includes('over') || selLower.includes('under')) {
    if (marketLower.includes('corner')) {
      return `${selection} Corners`
    } else if (marketLower.includes('card')) {
      return `${selection} Cards`
    } else {
      return `${selection} Goals`
    }
  }
  
  return selection
}

function MixedCard({ ticket, index }) {
  const gradientClass = index === 0 ? 'gradient-gold' 
    : index === 1 ? 'gradient-blue'
    : index === 2 ? 'gradient-purple'
    : 'gradient-red'
  
  return (
    <div className={`card-outer ${gradientClass}`}>
      <div className="card-inner">
        <div className="ticket-name">{ticket.ticket_name}</div>
        <div className="odds-bracket">{ticket.odds_bracket}</div>
        <div className="games-count">{ticket.num_games} GAMES</div>
        
        <div className="mixed-legs-container">
          {ticket.legs?.map((leg, i) => (
            <div key={i} className="mixed-leg-row">
              <div className="mixed-leg-teams">
                {leg.home} vs {leg.away}
              </div>
              <div className="mixed-leg-market">
                <span className="leg-selection">{formatSelectionWithMarket(leg.selection, leg.market)}</span>
                <span className="leg-odds">{leg.odds?.toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>
        
        <div className="combined-row">
          <span className="combined-label">COMBINED</span>
          <span className="combined-odds">{ticket.combined_odds?.toFixed(2)}</span>
        </div>
        
        <div className="confidence-row">
          <span className="confidence-label">CONFIDENCE</span>
          <span className="confidence-value">{ticket.combined_confidence}%</span>
        </div>
        <div className="progress-bg">
          <div className="progress-fill" style={{ width: `${ticket.combined_confidence}%` }} />
        </div>
      </div>
    </div>
  )
}

// ==========================================
// ADMIN CARDS PAGE
// ==========================================
function AdminCardsPage() {
  const [searchParams] = useSearchParams()
  const [sgpTickets, setSgpTickets] = useState([])
  const [mixedTickets, setMixedTickets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('sgp')

  const adminKey = searchParams.get('key')

  useEffect(() => {
    if (adminKey) {
      fetchCards()
    } else {
      setError('Admin key required')
      setLoading(false)
    }
  }, [adminKey])

  const fetchCards = async () => {
    try {
      const response = await fetch(`${API_URL}/admin/cards?key=${adminKey}`)
      if (!response.ok) {
        throw new Error('Invalid admin key')
      }
      const data = await response.json()
      setSgpTickets(data.build_a_bet?.tickets || [])
      setMixedTickets(data.mixed_parlay?.tickets || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <div className="loading-text">Loading admin cards...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-content">
        <Header />
        <div className="error-container">
          <IoLockClosed className="error-icon" />
          <div className="error-title">Access Denied</div>
          <div className="error-message">{error}</div>
          <div className="error-hint">Please use the correct admin URL with key parameter</div>
        </div>
      </div>
    )
  }

  return (
    <div className="page-content">
      <Header />
      
      <div className="admin-badge">
        <IoShield style={{ color: '#22c55e' }} />
        <span>ADMIN ACCESS</span>
      </div>
      
      <div className="admin-tabs">
        <button 
          className={`admin-tab ${activeTab === 'sgp' ? 'active' : ''}`}
          onClick={() => setActiveTab('sgp')}
        >
          BUILD A BET
        </button>
        <button 
          className={`admin-tab ${activeTab === 'mixed' ? 'active' : ''}`}
          onClick={() => setActiveTab('mixed')}
        >
          MIXED PARLAY
        </button>
      </div>
      
      {activeTab === 'sgp' && (
        <>
          <div className="market-header" style={{ color: '#f59e0b' }}>
            SAME GAME PARLAY - BUILD A BET
          </div>
          
          <div className="legend-row">
            <div className="legend-item">
              <div className="legend-dot safe" />
              <span>SAFE 1.90-3.00</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot value" />
              <span>VALUE 3.01-4.00</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot high" />
              <span>HIGH 4.01-7.00</span>
            </div>
          </div>
          
          <div className="cards-grid">
            <div className="cards-row">
              {sgpTickets.slice(0, 2).map((ticket, i) => <SGPCard key={ticket.id} ticket={ticket} index={i} />)}
            </div>
            <div className="cards-row">
              {sgpTickets.slice(2, 4).map((ticket, i) => <SGPCard key={ticket.id} ticket={ticket} index={i + 2} />)}
            </div>
          </div>
        </>
      )}
      
      {activeTab === 'mixed' && (
        <>
          <div className="market-header" style={{ color: '#3b82f6' }}>
            MIXED GAMES PARLAY
          </div>
          
          <div className="legend-row">
            <div className="legend-item">
              <div className="legend-dot safe" />
              <span>3.50-5.00</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot value" />
              <span>5.01-6.50</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot mid" />
              <span>6.51-8.00</span>
            </div>
            <div className="legend-item">
              <div className="legend-dot high" />
              <span>8.01-12.00</span>
            </div>
          </div>
          
          <div className="cards-grid">
            <div className="cards-row">
              {mixedTickets.slice(0, 2).map((ticket, i) => <MixedCard key={ticket.id} ticket={ticket} index={i} />)}
            </div>
            <div className="cards-row">
              {mixedTickets.slice(2, 4).map((ticket, i) => <MixedCard key={ticket.id} ticket={ticket} index={i + 2} />)}
            </div>
          </div>
        </>
      )}
      
      <div className="bottom-section">
        <div className="features-row">
          <div className="feature-item">
            <IoHardwareChip className="feature-icon" style={{ color: '#f59e0b' }} />
            <span className="feature-title">AI POWERED</span>
          </div>
          <div className="feature-item">
            <IoFlame className="feature-icon" style={{ color: '#ef4444' }} />
            <span className="feature-title">13 MARKETS</span>
          </div>
          <div className="feature-item">
            <IoTrendingUp className="feature-icon" style={{ color: '#22c55e' }} />
            <span className="feature-title">MOST PROBABLE</span>
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

export default AdminCardsPage
