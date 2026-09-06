import React, { useState, useEffect } from 'react'
import Header from '../components/Header'
import { BuyCoinsModal, SubscriptionModal, AccessOptionsModal } from '../components/CoinWallet'
import { IoLockClosed, IoCheckmarkCircle, IoTicket, IoTime, IoWarning, IoFlash, IoWallet } from 'react-icons/io5'

const API_URL = '/api'
const COIN_COST_BETSLIP = 10

/**
 * Helper function to format selection with full market type (Goals/Cards/Corners)
 * This is a PERMANENT DEFAULT - all selections must specify the market type clearly
 */
function formatSelectionWithMarket(selection, market) {
  if (!selection) return selection
  
  const selLower = selection.toLowerCase()
  const marketLower = (market || '').toLowerCase()
  
  // If selection already includes market type, return as-is
  if (selLower.includes('goal') || selLower.includes('corner') || selLower.includes('card') || 
      selLower.includes('btts') || selLower.includes('both teams') || 
      selLower.includes('win') || selLower.includes('1x') || 
      selLower.includes('x2') || selLower.includes('12') ||
      selLower.includes('double chance') || selLower.includes('draw')) {
    return selection
  }
  
  // Add market type based on selection pattern (Over/Under)
  if (selLower.includes('over') || selLower.includes('under')) {
    if (marketLower.includes('corner')) {
      return `${selection} Corners`
    } else if (marketLower.includes('card')) {
      return `${selection} Cards`
    } else {
      // Default to Goals for over/under markets
      return `${selection} Goals`
    }
  }
  
  return selection
}

// Odds range options
const ODDS_RANGES = [
  { key: 'safe', label: '1.80-3.00', description: 'Safe', color: '#16a34a' },
  { key: 'value', label: '3.01-7.00', description: 'Value', color: '#3b82f6' },
  { key: 'risky', label: '7.01-12.00', description: 'Risky', color: '#f59e0b' },
  { key: 'high_risk', label: '12.01-20.00', description: 'High Risk', color: '#f97316' },
  { key: 'very_high', label: '20.01-50.00', description: 'Very High', color: '#ef4444' },
  { key: 'extreme', label: '50.01-99.00', description: 'Extreme', color: '#dc2626' },
  { key: 'jackpot', label: '100+', description: 'Jackpot', color: '#8b5cf6' },
]

// Market type options - 9 options for Ticket Machine
const MARKET_TYPES = [
  { key: 'all', label: 'All' },
  { key: 'btts', label: 'BTTS' },
  { key: 'win', label: 'Win' },
  { key: 'dc_goals', label: 'DC and Goals' },
  { key: 'over25', label: 'O2.5 Goals' },
  { key: 'over15', label: 'O1.5 Goals' },
  { key: 'under35', label: 'U3.5 Goals' },
  { key: 'corners_1h', label: 'O4.5 1H Corners' },
  { key: 'cards', label: 'O3.5 Cards' },
]

function TicketLeg({ leg, index }) {
  return (
    <div className="ticket-leg-row">
      <div className="leg-num-badge">{index + 1}</div>
      <div className="leg-info">
        <div className="leg-match-names">
          {leg.home} <span className="leg-match-vs">vs</span> {leg.away}
        </div>
        <div className="leg-league-name">{leg.league}</div>
        <div className="leg-pick-row">
          <IoCheckmarkCircle className="leg-pick-check" />
          <span className="leg-pick-text">{formatSelectionWithMarket(leg.selection, leg.market)}</span>
          <span className="leg-pick-odds">@ {leg.odds}</span>
        </div>
      </div>
    </div>
  )
}

function GeneratedTicket({ ticket }) {
  if (!ticket) return null
  
  const confClass = ticket.confidence?.toLowerCase() === 'high' ? 'conf-high' 
    : ticket.confidence?.toLowerCase() === 'medium' ? 'conf-medium' 
    : 'conf-low'
  
  return (
    <div className="generated-ticket-card">
      <div className="ticket-card-header">
        <div className="ticket-card-badge">
          <IoTicket />
          <span>YOUR TICKET</span>
        </div>
        <div className="ticket-card-meta">
          {ticket.odds_range} • {ticket.market_type}
        </div>
      </div>
      
      {ticket.markets_mixed && ticket.mix_notice && (
        <div className="ticket-mix-notice">
          <IoWarning />
          <span>{ticket.mix_notice}</span>
        </div>
      )}
      
      <div className="ticket-legs-container">
        {ticket.legs?.map((leg, i) => (
          <TicketLeg key={i} leg={leg} index={i} />
        ))}
      </div>
      
      <div className="ticket-summary-bar">
        <div className="summary-item">
          <span className="summary-item-label">Legs</span>
          <span className="summary-item-value">{ticket.num_legs}</span>
        </div>
        <div className="summary-item">
          <span className="summary-item-label">Combined Odds</span>
          <span className="summary-item-value odds">{ticket.combined_odds}</span>
        </div>
        <div className="summary-item">
          <span className="summary-item-label">Confidence</span>
          <span className={`summary-item-value ${confClass}`}>{ticket.confidence}</span>
        </div>
      </div>
    </div>
  )
}

function TicketMachinePage() {
  const [selectedOdds, setSelectedOdds] = useState(null)
  const [selectedMarket, setSelectedMarket] = useState(null)
  const [generatedTicket, setGeneratedTicket] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  // Coin & subscription state
  const [walletInfo, setWalletInfo] = useState({ balance: 0, is_subscribed: false })
  const [dailyFreeUsed, setDailyFreeUsed] = useState(false)
  const [ticketsGenerated, setTicketsGenerated] = useState(0)
  const [showBuyCoins, setShowBuyCoins] = useState(false)
  const [showSubscription, setShowSubscription] = useState(false)
  const [showAccessOptions, setShowAccessOptions] = useState(false)

  useEffect(() => {
    fetchWalletInfo()
  }, [])

  const fetchWalletInfo = async () => {
    try {
      const response = await fetch(`${API_URL}/wallet/balance`)
      const data = await response.json()
      setWalletInfo(data)
      setDailyFreeUsed(data.daily_free_betslip_used || false)
    } catch (error) {
      console.error('Error fetching wallet:', error)
    }
  }

  const handleUseDailyFree = async () => {
    try {
      const response = await fetch(`${API_URL}/wallet/use-daily-free?feature=ticket_machine`, {
        method: 'POST'
      })
      const data = await response.json()
      
      if (data.success) {
        setDailyFreeUsed(true)
        return true
      }
      return false
    } catch (error) {
      console.error('Error using daily free:', error)
      return false
    }
  }

  const handleSpendCoins = async () => {
    if (walletInfo.balance < COIN_COST_BETSLIP) {
      setShowAccessOptions(true)
      return false
    }
    
    try {
      const response = await fetch(`${API_URL}/wallet/spend?amount=${COIN_COST_BETSLIP}&spend_type=ticket_machine`, {
        method: 'POST'
      })
      const data = await response.json()
      
      if (data.success) {
        setWalletInfo(prev => ({ ...prev, balance: data.new_balance }))
        return true
      }
      return false
    } catch (error) {
      console.error('Error spending coins:', error)
      return false
    }
  }
  
  const handleGenerate = async () => {
    if (!selectedOdds || !selectedMarket) {
      setError('Please select both odds range and market type')
      return
    }

    // Determine if this is a free ticket or paid
    const canUseFree = walletInfo.is_subscribed && !dailyFreeUsed
    const needsCoins = !canUseFree

    if (needsCoins) {
      if (walletInfo.balance < COIN_COST_BETSLIP) {
        setShowAccessOptions(true)
        return
      }
      const spent = await handleSpendCoins()
      if (!spent) return
    } else {
      const usedFree = await handleUseDailyFree()
      if (!usedFree) return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(
        `${API_URL}/ticket-machine/generate?odds_range=${selectedOdds}&market_type=${selectedMarket}`,
        { method: 'POST' }
      )
      const data = await response.json()
      
      if (data.success) {
        setGeneratedTicket(data.ticket)
        setTicketsGenerated(prev => prev + 1)
      } else {
        setError(data.detail || 'Failed to generate ticket')
      }
    } catch (err) {
      setError('Failed to connect to server')
    } finally {
      setLoading(false)
    }
  }

  const handleAccessOption = (option) => {
    setShowAccessOptions(false)
    if (option === 'subscribe') {
      setShowSubscription(true)
    } else {
      setShowBuyCoins(true)
    }
  }

  const handlePurchaseComplete = () => {
    fetchWalletInfo()
  }

  // Can generate for free?
  const canUseFreeTicket = walletInfo.is_subscribed && !dailyFreeUsed
  const canGenerateWithCoins = walletInfo.balance >= COIN_COST_BETSLIP
  const canGenerate = canUseFreeTicket || canGenerateWithCoins
  
  return (
    <div className="page-content">
      <Header />
      
      <div className="ticket-machine-header">
        <div className="ticket-machine-title">Ticket Machine</div>
        <div className="ticket-machine-subtitle">Build Your Custom Betslip</div>
      </div>
      
      {/* Access Info */}
      <div className="ticket-machine-access-info">
        {walletInfo.is_subscribed ? (
          <div className="tm-status subscribed">
            <IoCheckmarkCircle />
            <div className="tm-status-content">
              <span className="tm-status-title">Subscriber</span>
              <span className="tm-status-desc">
                {canUseFreeTicket ? '1 FREE betslip available' : 'Daily free used • 50 coins per betslip'}
              </span>
            </div>
          </div>
        ) : (
          <div className="tm-status not-subscribed">
            <IoWallet />
            <div className="tm-status-content">
              <span className="tm-status-title">{COIN_COST_BETSLIP} Coins per Betslip</span>
              <span className="tm-status-desc">
                <button onClick={() => setShowSubscription(true)} className="inline-link">Subscribe</button> for 1 free daily
              </span>
            </div>
          </div>
        )}
        
        <div className="tm-balance">
          <IoWallet />
          <span>{walletInfo.balance.toLocaleString()}</span>
        </div>
      </div>
      
      {/* Odds Selection */}
      <div className="selection-section">
        <div className="section-label">SELECT ODDS RANGE</div>
        <div className="odds-options-grid">
          {ODDS_RANGES.map((range) => (
            <button
              key={range.key}
              className={`odds-btn ${selectedOdds === range.key ? 'selected' : ''}`}
              onClick={() => setSelectedOdds(range.key)}
              style={{ 
                borderColor: selectedOdds === range.key ? range.color : '#e5e7eb',
                backgroundColor: selectedOdds === range.key ? `${range.color}15` : '#f8f9fa'
              }}
            >
              <span className="odds-btn-label" style={{ color: range.color }}>{range.label}</span>
              <span className="odds-btn-desc">{range.description}</span>
            </button>
          ))}
        </div>
      </div>
      
      {/* Market Selection */}
      <div className="selection-section">
        <div className="section-label">SELECT MARKET</div>
        <div className="market-options-grid">
          {MARKET_TYPES.map((market) => (
            <button
              key={market.key}
              className={`market-btn ${selectedMarket === market.key ? 'selected' : ''}`}
              onClick={() => setSelectedMarket(market.key)}
            >
              {market.label}
            </button>
          ))}
        </div>
      </div>
      
      {/* Generate Button */}
      <div className="generate-section">
        {error && <div className="error-msg">{error}</div>}
        
        <button 
          className={`generate-btn ${!canGenerate && !canUseFreeTicket ? 'low-balance' : ''}`}
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading ? (
            <span>Generating...</span>
          ) : canUseFreeTicket ? (
            <>
              <IoCheckmarkCircle />
              <span>Generate FREE Ticket</span>
            </>
          ) : (
            <>
              <IoWallet />
              <span>Generate for {COIN_COST_BETSLIP} Coins</span>
            </>
          )}
        </button>
        
        {!canGenerate && !canUseFreeTicket && (
          <div className="low-balance-notice">
            <IoWarning />
            <span>Insufficient coins. </span>
            <button onClick={() => setShowBuyCoins(true)} className="inline-link">Buy more</button>
            <span> or </span>
            <button onClick={() => setShowSubscription(true)} className="inline-link">Subscribe</button>
          </div>
        )}
        
        <div className="market-note">
          <IoWarning className="note-icon" />
          <span>
            Note: If your selected market cannot fulfill the target odds, other markets may be automatically added to reach the desired odds range.
          </span>
        </div>
      </div>
      
      {/* Generated Ticket */}
      {generatedTicket && <GeneratedTicket ticket={generatedTicket} />}
      
      {/* Session Stats */}
      {ticketsGenerated > 0 && (
        <div className="session-stats">
          <IoTicket />
          <span>Tickets generated this session: {ticketsGenerated}</span>
        </div>
      )}
      
      {/* Expiry Notice */}
      <div className="expiry-notice">
        <IoTime />
        <span>All tickets expire at midnight (00:00). Unused tickets are forfeited.</span>
      </div>
      
      {/* Footer */}
      <div className="footer-section">
        <div className="powered-text">POWERED BY AI. DRIVEN BY DATA. DELIVERING RESULTS.</div>
        <div className="brand-signature">OkaMoney AI Tips ✓</div>
      </div>

      <div className="disclaimer">
        <span className="disclaimer-icon">⚠️</span>
        <span className="disclaimer-text">
          OkaMoney AI Tips provides predictions for informational purposes only. Predictions are probability based, not guaranteed wins. Please gamble responsibly.
        </span>
      </div>

      {/* Coin Modals */}
      <BuyCoinsModal 
        isOpen={showBuyCoins}
        onClose={() => setShowBuyCoins(false)}
        onPurchaseComplete={handlePurchaseComplete}
      />

      <SubscriptionModal
        isOpen={showSubscription}
        onClose={() => setShowSubscription(false)}
        onSubscribeComplete={handlePurchaseComplete}
      />

      <AccessOptionsModal
        isOpen={showAccessOptions}
        onClose={() => setShowAccessOptions(false)}
        onSelectOption={handleAccessOption}
      />
    </div>
  )
}

export default TicketMachinePage
