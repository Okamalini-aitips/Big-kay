import React, { useState, useEffect } from 'react'
import Header from '../components/Header'
import { BuyCoinsModal, SubscriptionModal, AccessOptionsModal } from '../components/CoinWallet'
import { IoLockClosed, IoCheckmarkCircle, IoConstruct, IoCloseCircle, IoCalendarOutline, IoTrophyOutline, IoWallet } from 'react-icons/io5'

const API_URL = '/api'
const COIN_COST_TICKET = 4

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

function BetslipCard({ ticket, index, isLocked, isYesterday }) {
  const overallResult = ticket.overall_result
  
  return (
    <div className={`betslip-card ${isLocked ? 'locked' : ''} ${isYesterday ? 'yesterday' : ''}`}>
      <div className="betslip-card-header">
        <div className="betslip-label">
          <IoConstruct className="betslip-badge-icon" />
          <span>BUILD A BET #{index + 1}</span>
        </div>
        {isYesterday ? (
          <div className={`ticket-result-badge ${overallResult}`}>
            {overallResult === 'won' ? (
              <>
                <IoCheckmarkCircle /> WON
              </>
            ) : (
              <>
                <IoCloseCircle /> LOST
              </>
            )}
          </div>
        ) : isLocked ? (
          <IoLockClosed className="betslip-lock" />
        ) : (
          <IoCheckmarkCircle className="betslip-unlock" />
        )}
      </div>
      
      {isLocked && !isYesterday ? (
        <div className="locked-betslip-body">
          <IoLockClosed className="locked-icon-big" />
          <span className="locked-msg">Subscribe to unlock</span>
          <span className="locked-hint">{ticket.legs?.length || 3} legs • Same Game Parlay</span>
        </div>
      ) : (
        <>
          <div className="betslip-match-info">
            <div className="betslip-league">{ticket.match?.league}</div>
            <div className="betslip-teams">
              {ticket.match?.home} vs {ticket.match?.away}
            </div>
          </div>
          
          <div className="betslip-legs-list">
            {ticket.legs?.map((leg, i) => (
              <div key={i} className="betslip-leg-item">
                {isYesterday ? (
                  <span className={`leg-result-icon ${leg.result}`}>
                    {leg.result === 'won' ? <IoCheckmarkCircle /> : <IoCloseCircle />}
                  </span>
                ) : (
                  <IoCheckmarkCircle className="leg-check-icon" />
                )}
                <span className="leg-selection-text">
                  {formatSelectionWithMarket(leg.selection, leg.market)}
                </span>
                <span className="leg-odds-text">@ {leg.odds?.toFixed(2)}</span>
              </div>
            ))}
          </div>
          
          <div className="betslip-footer-bar">
            <div className="combined-odds-display">
              <span className="odds-label-sm">Combined Odds</span>
              <span className="odds-value-lg">{ticket.combined_odds?.toFixed(2)}</span>
            </div>
            <span className="confidence-badge-sm">{ticket.combined_confidence}%</span>
          </div>
        </>
      )}
    </div>
  )
}

function BuildABetPage() {
  const [betslips, setBetslips] = useState([])
  const [yesterdayBetslips, setYesterdayBetslips] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('today') // 'today' or 'yesterday'
  
  // Coin & subscription state
  const [walletInfo, setWalletInfo] = useState({ balance: 0, is_subscribed: false })
  const [unlockedTickets, setUnlockedTickets] = useState(new Set())
  const [dailyFreeUsed, setDailyFreeUsed] = useState(false)
  const [showBuyCoins, setShowBuyCoins] = useState(false)
  const [showSubscription, setShowSubscription] = useState(false)
  const [showAccessOptions, setShowAccessOptions] = useState(false)

  useEffect(() => {
    fetchBetslips()
    fetchWalletInfo()
  }, [])

  const fetchWalletInfo = async () => {
    try {
      const response = await fetch(`${API_URL}/wallet/balance`)
      const data = await response.json()
      setWalletInfo(data)
      setDailyFreeUsed(data.daily_free_build_bet_used || false)
    } catch (error) {
      console.error('Error fetching wallet:', error)
    }
  }

  const fetchBetslips = async () => {
    try {
      // Fetch today's SGP
      const todayResponse = await fetch(`${API_URL}/sgp`)
      const todayData = await todayResponse.json()
      setBetslips((todayData.sgp_picks || []).slice(0, 2))
      
      // Fetch yesterday's SGP
      const yesterdayResponse = await fetch(`${API_URL}/sgp/yesterday`)
      const yesterdayData = await yesterdayResponse.json()
      setYesterdayBetslips(yesterdayData.sgp_picks || [])
    } catch (error) {
      console.error('Error fetching betslips:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUseDailyFree = async (ticketId) => {
    try {
      const response = await fetch(`${API_URL}/wallet/use-daily-free?feature=build_a_bet`, {
        method: 'POST'
      })
      const data = await response.json()
      
      if (data.success) {
        setDailyFreeUsed(true)
        setUnlockedTickets(prev => new Set([...prev, ticketId]))
      }
    } catch (error) {
      console.error('Error using daily free:', error)
    }
  }

  const handleUnlockWithCoins = async (ticketId) => {
    if (walletInfo.balance < COIN_COST_TICKET) {
      setShowAccessOptions(true)
      return
    }
    
    try {
      const response = await fetch(`${API_URL}/wallet/spend?amount=${COIN_COST_TICKET}&spend_type=build_a_bet&item_id=${ticketId}`, {
        method: 'POST'
      })
      const data = await response.json()
      
      if (data.success) {
        setUnlockedTickets(prev => new Set([...prev, ticketId]))
        setWalletInfo(prev => ({ ...prev, balance: data.new_balance }))
      }
    } catch (error) {
      console.error('Error unlocking ticket:', error)
    }
  }

  const isTicketUnlocked = (ticketId, index) => {
    if (walletInfo.is_subscribed) {
      // Subscribers get first ticket free
      if (index === 0 && !dailyFreeUsed) return true
      return unlockedTickets.has(ticketId)
    }
    return unlockedTickets.has(ticketId)
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
  
  // Calculate yesterday's stats
  const yesterdayStats = () => {
    const total = yesterdayBetslips.length
    const won = yesterdayBetslips.filter(t => t.overall_result === 'won').length
    return { total, won, lost: total - won }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <div className="loading-text">Loading Build A Bet...</div>
      </div>
    )
  }

  const stats = yesterdayStats()

  return (
    <div className="page-content">
      <Header />
      
      <div className="betslip-page-title">Build A Bet</div>
      
      {/* Date Tabs */}
      <div className="date-tabs">
        <button 
          className={`date-tab ${activeTab === 'yesterday' ? 'active' : ''}`}
          onClick={() => setActiveTab('yesterday')}
        >
          <IoCalendarOutline />
          <span>Yesterday</span>
        </button>
        <button 
          className={`date-tab ${activeTab === 'today' ? 'active' : ''}`}
          onClick={() => setActiveTab('today')}
        >
          <IoCalendarOutline />
          <span>Today</span>
        </button>
      </div>
      
      <div className="betslip-info-bar">
        <IoConstruct className="betslip-info-icon" />
        <span>Same Game Parlay • {activeTab === 'today' ? '2 Daily Betslips' : 'Results'}</span>
      </div>
      
      {activeTab === 'yesterday' ? (
        <>
          {/* Yesterday Stats */}
          <div className="ticket-stats-summary">
            <div className="stat-box total">
              <IoTrophyOutline className="stat-box-icon" />
              <span className="stat-box-value">{stats.total}</span>
              <span className="stat-box-label">Tickets</span>
            </div>
            <div className="stat-box won">
              <IoCheckmarkCircle className="stat-box-icon" />
              <span className="stat-box-value">{stats.won}</span>
              <span className="stat-box-label">Won</span>
            </div>
            <div className="stat-box lost">
              <IoCloseCircle className="stat-box-icon" />
              <span className="stat-box-value">{stats.lost}</span>
              <span className="stat-box-label">Lost</span>
            </div>
          </div>
          
          <div className="betslip-list">
            {yesterdayBetslips.map((ticket, index) => (
              <BetslipCard 
                key={ticket.id} 
                ticket={ticket} 
                index={index} 
                isLocked={false}
                isYesterday={true}
              />
            ))}
          </div>
        </>
      ) : (
        <>
          {/* Access Info for Today */}
          <div className="ticket-access-info">
            {walletInfo.is_subscribed ? (
              <div className="access-status subscribed">
                <IoCheckmarkCircle />
                <span>{!dailyFreeUsed ? '1 FREE ticket available today' : 'Daily free used • Use coins for more'}</span>
              </div>
            ) : (
              <div className="access-status not-subscribed">
                <IoWallet />
                <span>{COIN_COST_TICKET} coins per ticket • <button onClick={() => setShowSubscription(true)} className="inline-link">Subscribe</button> for 1 free daily</span>
              </div>
            )}
          </div>
          
          <div className="betslip-list">
            {betslips.map((ticket, index) => {
              const unlocked = isTicketUnlocked(ticket.id, index)
              const canUseFree = walletInfo.is_subscribed && index === 0 && !dailyFreeUsed
              
              return (
                <div key={ticket.id}>
                  <BetslipCard 
                    ticket={ticket} 
                    index={index} 
                    isLocked={!unlocked && !canUseFree}
                    isYesterday={false}
                  />
                  {!unlocked && (
                    <div className="ticket-unlock-actions">
                      {canUseFree ? (
                        <button 
                          className="unlock-btn free-btn"
                          onClick={() => handleUseDailyFree(ticket.id)}
                        >
                          <IoCheckmarkCircle />
                          Use FREE Daily Ticket
                        </button>
                      ) : (
                        <button 
                          className="unlock-btn coins-btn"
                          onClick={() => handleUnlockWithCoins(ticket.id)}
                        >
                          <IoWallet />
                          Unlock for {COIN_COST_TICKET} Coins
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Balance Display */}
          <div className="balance-display">
            <IoWallet />
            <span>Your Balance: <strong>{walletInfo.balance.toLocaleString()} coins</strong></span>
            <button onClick={() => setShowBuyCoins(true)} className="buy-more-btn">Buy More</button>
          </div>
        </>
      )}
      
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

export default BuildABetPage
