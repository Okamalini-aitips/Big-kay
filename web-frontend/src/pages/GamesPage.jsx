import React, { useState, useEffect } from 'react'
import Header from '../components/Header'
import { BuyCoinsModal, SubscriptionModal, AccessOptionsModal } from '../components/CoinWallet'
import WhatsAppSubscriptionModal from '../components/WhatsAppSubscriptionModal'
import { 
  IoLogoWhatsapp, 
  IoSearch, 
  IoCheckmarkCircle, 
  IoLockClosed, 
  IoClose,
  IoTrophy,
  IoStatsChart,
  IoTime,
  IoCloseCircle,
  IoCalendarOutline,
  IoWallet
} from 'react-icons/io5'

const API_URL = '/api'
const COIN_COST_TIP = 1

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

// Country flag mapping (basic set)
const FLAG_EMOJIS = {
  'England': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
  'Spain': '🇪🇸',
  'Germany': '🇩🇪',
  'Italy': '🇮🇹',
  'France': '🇫🇷',
  'Portugal': '🇵🇹',
  'Netherlands': '🇳🇱',
  'Belgium': '🇧🇪',
  'Greece': '🇬🇷',
  'Turkey': '🇹🇷',
  'Argentina': '🇦🇷',
  'Brazil': '🇧🇷',
  'USA': '🇺🇸',
  'Mexico': '🇲🇽',
  'Denmark': '🇩🇰',
  'Sweden': '🇸🇪',
  'Norway': '🇳🇴',
  'Scotland': '🏴󠁧󠁢󠁳󠁣󠁴󠁿',
  'Austria': '🇦🇹',
  'Switzerland': '🇨🇭',
  'Poland': '🇵🇱',
  'Russia': '🇷🇺',
  'Ukraine': '🇺🇦',
  'Japan': '🇯🇵',
  'South Korea': '🇰🇷',
  'Australia': '🇦🇺',
  'Colombia': '🇨🇴',
  'Chile': '🇨🇱',
  'Saudi Arabia': '🇸🇦',
  'South Africa': '🇿🇦',
}

// Get country from league name
function getCountryFromLeague(league) {
  const leagueLower = league?.toLowerCase() || ''
  if (leagueLower.includes('premier league') || leagueLower.includes('efl') || leagueLower.includes('championship') || leagueLower.includes('england')) return 'England'
  if (leagueLower.includes('la liga') || leagueLower.includes('spain')) return 'Spain'
  if (leagueLower.includes('bundesliga') || leagueLower.includes('germany')) return 'Germany'
  if (leagueLower.includes('serie a') || leagueLower.includes('italy')) return 'Italy'
  if (leagueLower.includes('ligue 1') || leagueLower.includes('france')) return 'France'
  if (leagueLower.includes('primeira') || leagueLower.includes('portugal')) return 'Portugal'
  if (leagueLower.includes('eredivisie') || leagueLower.includes('netherlands')) return 'Netherlands'
  if (leagueLower.includes('pro league') || leagueLower.includes('belgium')) return 'Belgium'
  if (leagueLower.includes('super league greece') || leagueLower.includes('greece')) return 'Greece'
  if (leagueLower.includes('süper lig') || leagueLower.includes('turkey')) return 'Turkey'
  if (leagueLower.includes('liga profesional') || leagueLower.includes('argentina')) return 'Argentina'
  if (leagueLower.includes('brasileirão') || leagueLower.includes('brazil')) return 'Brazil'
  if (leagueLower.includes('mls') || leagueLower.includes('usa')) return 'USA'
  if (leagueLower.includes('liga mx') || leagueLower.includes('mexico')) return 'Mexico'
  if (leagueLower.includes('superligaen') || leagueLower.includes('denmark')) return 'Denmark'
  if (leagueLower.includes('allsvenskan') || leagueLower.includes('sweden')) return 'Sweden'
  if (leagueLower.includes('eliteserien') || leagueLower.includes('norway')) return 'Norway'
  if (leagueLower.includes('scottish') || leagueLower.includes('scotland')) return 'Scotland'
  if (leagueLower.includes('colombia')) return 'Colombia'
  if (leagueLower.includes('psl') || leagueLower.includes('south africa')) return 'South Africa'
  return 'England' // Default
}

function FormBadge({ result }) {
  return <span className={`form-badge ${result}`}>{result}</span>
}

function TipModal({ game, onClose }) {
  if (!game) return null

  // Generate mock stats for demonstration
  const homeStats = {
    position: Math.floor(Math.random() * 10) + 1,
    played: 5,
    won: Math.floor(Math.random() * 4) + 1,
    drawn: Math.floor(Math.random() * 2),
    lost: Math.floor(Math.random() * 2),
    gf: Math.floor(Math.random() * 10) + 5,
    ga: Math.floor(Math.random() * 8) + 2,
    pts: 0
  }
  homeStats.pts = homeStats.won * 3 + homeStats.drawn

  const awayStats = {
    position: Math.floor(Math.random() * 10) + 5,
    played: 5,
    won: Math.floor(Math.random() * 3) + 1,
    drawn: Math.floor(Math.random() * 2),
    lost: Math.floor(Math.random() * 3),
    gf: Math.floor(Math.random() * 8) + 3,
    ga: Math.floor(Math.random() * 10) + 3,
    pts: 0
  }
  awayStats.pts = awayStats.won * 3 + awayStats.drawn

  // Mock H2H data
  const h2hMatches = [
    { date: '15 Jul 26', home: game.match?.home, away: game.match?.away, score: '2-1' },
    { date: '20 Mar 26', home: game.match?.away, away: game.match?.home, score: '1-1' },
    { date: '08 Dec 25', home: game.match?.home, away: game.match?.away, score: '3-0' },
    { date: '14 Aug 25', home: game.match?.away, away: game.match?.home, score: '0-2' },
    { date: '22 Apr 25', home: game.match?.home, away: game.match?.away, score: '1-0' },
  ]

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Match Analysis</span>
          <button className="modal-close" onClick={onClose}>
            <IoClose />
          </button>
        </div>
        
        <div className="modal-body">
          {/* Match Info */}
          <div className="modal-match-info">
            <div className="modal-league">{game.match?.league}</div>
            <div className="modal-teams-display">
              {game.match?.home} <span className="vs">vs</span> {game.match?.away}
            </div>
            <div className="modal-time">
              <IoTime style={{ marginRight: '4px', verticalAlign: 'middle' }} />
              Today at 19:30
            </div>
          </div>

          {/* League Position */}
          <div className="stats-section">
            <div className="stats-title">
              <IoTrophy className="stats-icon" />
              League Position
            </div>
            <table className="position-table">
              <thead>
                <tr>
                  <th>Team</th>
                  <th>Pos</th>
                  <th>P</th>
                  <th>W</th>
                  <th>D</th>
                  <th>L</th>
                  <th>GF</th>
                  <th>GA</th>
                  <th>Pts</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{game.match?.home?.substring(0, 12)}</td>
                  <td><span className="pos-badge">{homeStats.position}</span></td>
                  <td>{homeStats.played}</td>
                  <td>{homeStats.won}</td>
                  <td>{homeStats.drawn}</td>
                  <td>{homeStats.lost}</td>
                  <td>{homeStats.gf}</td>
                  <td>{homeStats.ga}</td>
                  <td><strong>{homeStats.pts}</strong></td>
                </tr>
                <tr>
                  <td>{game.match?.away?.substring(0, 12)}</td>
                  <td><span className="pos-badge">{awayStats.position}</span></td>
                  <td>{awayStats.played}</td>
                  <td>{awayStats.won}</td>
                  <td>{awayStats.drawn}</td>
                  <td>{awayStats.lost}</td>
                  <td>{awayStats.gf}</td>
                  <td>{awayStats.ga}</td>
                  <td><strong>{awayStats.pts}</strong></td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Form */}
          <div className="stats-section">
            <div className="stats-title">
              <IoStatsChart className="stats-icon" />
              Last 5 Games (Overall)
            </div>
            <div className="form-display-row">
              <span className="form-team-name">{game.match?.home?.substring(0, 10)}</span>
              <div className="form-badges">
                {(game.home_form || 'WWDLW').split('').map((r, i) => (
                  <FormBadge key={`h${i}`} result={r} />
                ))}
              </div>
            </div>
            <div className="form-display-row">
              <span className="form-team-name">{game.match?.away?.substring(0, 10)}</span>
              <div className="form-badges">
                {(game.away_form || 'WDLDW').split('').map((r, i) => (
                  <FormBadge key={`a${i}`} result={r} />
                ))}
              </div>
            </div>
          </div>

          {/* H2H */}
          <div className="stats-section">
            <div className="stats-title">
              <IoStatsChart className="stats-icon" />
              Head to Head (Last 5)
            </div>
            {h2hMatches.map((match, i) => (
              <div key={i} className="h2h-item">
                <span className="h2h-date">{match.date}</span>
                <span className="h2h-teams">{match.home} vs {match.away}</span>
                <span className="h2h-score">{match.score}</span>
              </div>
            ))}
          </div>

          {/* Predictions */}
          <div className="stats-section">
            <div className="stats-title">
              <IoCheckmarkCircle className="stats-icon" />
              Our Predictions
            </div>
            {game.markets?.slice(0, 3).map((market, i) => (
              <div key={i} className="prediction-item">
                <IoCheckmarkCircle className="prediction-check" />
                <span className="prediction-text">
                  {formatSelectionWithMarket(market.selection, market.market)}
                </span>
                <span className="prediction-odds">@ {Number(market.odds).toFixed(2)}</span>
                {market.probability != null && (
                  <span className="prediction-prob">{market.probability}%</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function WhatsAppBanner({ onJoinClick }) {
  return (
    <div className="whatsapp-banner">
      <IoLogoWhatsapp className="whatsapp-icon" />
      <div className="banner-text">
        <div className="banner-title">PREMIUM DAILY BETSLIPS</div>
        <div className="banner-desc">2-4 betslips @ 1.90-5.50 odds daily</div>
        <div className="banner-price">Only R125/month</div>
        <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.9)', marginTop: '4px' }}>
          📱 072 517 7829
        </div>
      </div>
      <button onClick={onJoinClick} className="banner-cta">
        Join Now
      </button>
    </div>
  )
}

function MatchItem({ game, isFree, onTipClick, isYesterday }) {
  const kickoffTime = game.kickoff_time || '19:30'
  
  // Calculate overall result for the game's predictions
  const getOverallResult = () => {
    if (!isYesterday || !game.markets) return null
    const wonCount = game.markets.filter(m => m.result === 'won').length
    const totalCount = game.markets.length
    return { wonCount, totalCount, allWon: wonCount === totalCount }
  }
  
  const result = getOverallResult()
  
  return (
    <div className="match-item">
      <span className="match-time">{kickoffTime}</span>
      <div className="match-teams">
        <div className="team-name">{game.match?.home}</div>
        <div className="team-name">{game.match?.away}</div>
      </div>
      {isYesterday ? (
        <div className="result-indicators">
          {game.markets?.map((market, idx) => (
            <span key={idx} className={`result-icon ${market.result}`}>
              {market.result === 'won' ? <IoCheckmarkCircle /> : <IoCloseCircle />}
            </span>
          ))}
        </div>
      ) : (
        <button 
          className={`tip-button ${!isFree ? 'locked' : ''}`}
          onClick={() => isFree && onTipClick(game)}
        >
          {isFree ? 'TIP' : <IoLockClosed />}
        </button>
      )}
    </div>
  )
}

function CompetitionGroup({ league, matches, isFree, onTipClick, isYesterday }) {
  const country = getCountryFromLeague(league)
  const flag = FLAG_EMOJIS[country] || '🏳️'
  
  return (
    <div className="competition-group">
      <div className="competition-header">
        <span className="country-flag">{flag}</span>
        <span className="competition-name">{league}</span>
        <span className="match-count">({matches.length} {matches.length === 1 ? 'match' : 'matches'})</span>
      </div>
      {matches.map(game => (
        <MatchItem 
          key={game.id} 
          game={game} 
          isFree={isFree}
          onTipClick={onTipClick}
          isYesterday={isYesterday}
        />
      ))}
    </div>
  )
}

function ResultIcon({ result }) {
  if (result === 'won') return <IoCheckmarkCircle className="result-icon won" />
  if (result === 'lost') return <IoCloseCircle className="result-icon lost" />
  return <IoTime className="result-icon pending" />
}

function ResultsView({ data, selectedDate, onSelectDate }) {
  const days = data?.days || []
  if (days.length === 0) {
    return <div className="empty-state">No results yet. Check back after games are settled.</div>
  }
  const day = days.find(d => d.date === selectedDate) || days[0]
  const s = day.summary || {}
  const dayLabel = (dstr) => {
    const dt = new Date(dstr)
    const names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    const mon = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    return `${names[dt.getDay()]} ${String(dt.getDate()).padStart(2,'0')} ${mon[dt.getMonth()]}`
  }
  return (
    <>
      <div className="date-tabs" style={{ marginBottom: '8px' }}>
        {days.map(d => (
          <button key={d.date}
            className={`date-tab ${d.date === day.date ? 'active' : ''}`}
            onClick={() => onSelectDate(d.date)}>
            <IoCalendarOutline />
            <span>{dayLabel(d.date)}</span>
          </button>
        ))}
      </div>

      <div className="results-legend">
        <span className="legend-item won"><IoCheckmarkCircle /> Won</span>
        <span className="legend-item lost"><IoCloseCircle /> Lost</span>
        <span className="legend-item"><IoTime /> Pending</span>
      </div>

      <div className="yesterday-stats">
        <div className="stat-item"><span className="stat-value">{s.settled + s.pending || 0}</span><span className="stat-label">Total</span></div>
        <div className="stat-item won"><span className="stat-value">{s.won || 0}</span><span className="stat-label">Won</span></div>
        <div className="stat-item lost"><span className="stat-value">{s.lost || 0}</span><span className="stat-label">Lost</span></div>
        <div className="stat-item rate"><span className="stat-value">{s.hit_rate != null ? `${s.hit_rate}%` : '—'}</span><span className="stat-label">Hit Rate</span></div>
      </div>
      {s.settled === 0 && (
        <div className="disclaimer" style={{ marginTop: '4px' }}>
          <span className="disclaimer-icon">⏳</span>
          <span className="disclaimer-text">These picks are awaiting their final results.</span>
        </div>
      )}

      {(day.whatsapp || []).length > 0 && (
        <div className="competition-group">
          <div className="competition-header"><IoLogoWhatsapp /> <span className="competition-name">WhatsApp Daily Tickets</span></div>
          {day.whatsapp.map((t, i) => (
            <div key={i} className="wa-ticket">
              <div className="wa-ticket-name">{t.name}</div>
              {t.legs.map((leg, j) => (
                <div key={j} className="prediction-item">
                  <ResultIcon result={leg.result} />
                  <span className="prediction-text">{leg.home} v {leg.away}: {leg.selection}</span>
                  <span className="prediction-odds">@ {Number(leg.odds).toFixed(2)}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {(day.games || []).map((g, i) => (
        <div key={i} className="competition-group">
          <div className="competition-header">
            <span className="competition-name">{g.home} vs {g.away}</span>
            <span className="match-count">{g.league}</span>
          </div>
          {g.tips.map((tip, j) => (
            <div key={j} className="prediction-item">
              <ResultIcon result={tip.result} />
              <span className="prediction-text">{tip.selection}</span>
              <span className="prediction-odds">@ {Number(tip.odds).toFixed(2)}</span>
            </div>
          ))}
        </div>
      ))}
    </>
  )
}

function GamesPage() {
  const [games, setGames] = useState([])
  const [recentData, setRecentData] = useState({ days: [] })
  const [selectedResultDate, setSelectedResultDate] = useState(null)
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedGame, setSelectedGame] = useState(null)
  const [activeTab, setActiveTab] = useState('today') // 'today' or 'yesterday'
  
  // Coin & subscription state
  const [walletInfo, setWalletInfo] = useState({ balance: 0, is_subscribed: false })
  const [unlockedGames, setUnlockedGames] = useState(new Set())
  const [showBuyCoins, setShowBuyCoins] = useState(false)
  const [showSubscription, setShowSubscription] = useState(false)
  const [showAccessOptions, setShowAccessOptions] = useState(false)
  const [showWhatsAppModal, setShowWhatsAppModal] = useState(false)

  useEffect(() => {
    fetchGames()
    fetchWalletInfo()
  }, [])

  const fetchWalletInfo = async () => {
    try {
      const response = await fetch(`${API_URL}/wallet/balance`)
      const data = await response.json()
      setWalletInfo(data)
    } catch (error) {
      console.error('Error fetching wallet:', error)
    }
  }

  const fetchGames = async () => {
    try {
      // Fetch today's games
      const todayResponse = await fetch(`${API_URL}/games?limit=100`)
      const todayData = await todayResponse.json()
      setGames(todayData.games || [])
      
      // Fetch last 3 days of real results
      const recentResponse = await fetch(`${API_URL}/results/recent?days=3`)
      const recent = await recentResponse.json()
      setRecentData(recent)
      if (recent.days && recent.days.length > 0) {
        setSelectedResultDate(recent.days[0].date)
      }
    } catch (error) {
      console.error('Error fetching games:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUnlockWithCoins = async (game) => {
    if (walletInfo.balance < COIN_COST_TIP) {
      setShowAccessOptions(true)
      return
    }
    
    try {
      const response = await fetch(`${API_URL}/wallet/spend?amount=${COIN_COST_TIP}&spend_type=view_tip&item_id=${game.id}`, {
        method: 'POST'
      })
      const data = await response.json()
      
      if (data.success) {
        setUnlockedGames(prev => new Set([...prev, game.id]))
        setWalletInfo(prev => ({ ...prev, balance: data.new_balance }))
        setSelectedGame(game)
      }
    } catch (error) {
      console.error('Error unlocking game:', error)
    }
  }

  const handleTipClick = (game) => {
    // For free games or subscribed users or already unlocked
    if (game.is_free || walletInfo.is_subscribed || unlockedGames.has(game.id)) {
      setSelectedGame(game)
    } else {
      // Show unlock options for premium games
      setSelectedGame(game)
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

  // Get today's date formatted nicely
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  
  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  
  const formattedToday = `${dayNames[today.getDay()]} ${String(today.getDate()).padStart(2, '0')} ${monthNames[today.getMonth()]} ${String(today.getFullYear()).slice(-2)}`
  const formattedYesterday = `${dayNames[yesterday.getDay()]} ${String(yesterday.getDate()).padStart(2, '0')} ${monthNames[yesterday.getMonth()]} ${String(yesterday.getFullYear()).slice(-2)}`

  // Today's games for the "today" tab
  const currentGames = games

  // Filter games by search
  const filteredGames = currentGames.filter(game => {
    const searchLower = searchTerm.toLowerCase()
    return (
      game.match?.home?.toLowerCase().includes(searchLower) ||
      game.match?.away?.toLowerCase().includes(searchLower) ||
      game.match?.league?.toLowerCase().includes(searchLower)
    )
  })

  const freeGames = filteredGames.filter(g => g.is_free)
  const premiumGames = filteredGames.filter(g => !g.is_free)

  // Group games by league
  const groupByLeague = (gamesList) => {
    const grouped = {}
    gamesList.forEach(game => {
      const league = game.match?.league || 'Unknown League'
      if (!grouped[league]) {
        grouped[league] = []
      }
      grouped[league].push(game)
    })
    return grouped
  }

  const freeGrouped = groupByLeague(freeGames)
  const premiumGrouped = groupByLeague(premiumGames)

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <div className="loading-text">Loading predictions...</div>
      </div>
    )
  }

  return (
    <div className="page-content">
      <Header />
      
      <WhatsAppBanner onJoinClick={() => setShowWhatsAppModal(true)} />
      
      <div className="section-title-main">
        {activeTab === 'today' ? "Today's Predictions" : "Recent Results (Last 3 Days)"}
      </div>
      
      {/* Date Tabs */}
      <div className="date-tabs">
        <button 
          className={`date-tab ${activeTab === 'yesterday' ? 'active' : ''}`}
          onClick={() => setActiveTab('yesterday')}
        >
          <IoStatsChart />
          <span>Results</span>
        </button>
        <button 
          className={`date-tab ${activeTab === 'today' ? 'active' : ''}`}
          onClick={() => setActiveTab('today')}
        >
          <IoCalendarOutline />
          <span>Today</span>
        </button>
      </div>
      
      {activeTab === 'today' && (
        <div className="date-display">{formattedToday}</div>
      )}
      
      {/* Search (today only) */}
      {activeTab === 'today' && (
      <div className="search-container">
        <div className="search-wrapper">
          <IoSearch className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search country..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>
      )}

      {activeTab === 'yesterday' ? (
        <ResultsView
          data={recentData}
          selectedDate={selectedResultDate}
          onSelectDate={setSelectedResultDate}
        />
      ) : (
        <>
          {/* Subscriber Status Banner */}
          {walletInfo.is_subscribed ? (
            <div className="subscriber-status-banner">
              <IoCheckmarkCircle className="status-icon" />
              <span>You're subscribed! All predictions unlocked.</span>
            </div>
          ) : null}
          
          {/* Free Tier */}
          <div className="tier-header free">
            <IoCheckmarkCircle className="tier-icon" />
            <span>FREE TIER ({freeGames.length} games)</span>
          </div>
          
          {Object.entries(freeGrouped).map(([league, matches]) => (
            <CompetitionGroup 
              key={league}
              league={league}
              matches={matches}
              isFree={true}
              onTipClick={handleTipClick}
              isYesterday={false}
            />
          ))}

          {/* Premium Tier */}
          <div className="tier-header premium" style={{ marginTop: '20px' }}>
            <IoLockClosed className="tier-icon" />
            <span>PREMIUM TIER ({premiumGames.length} games)</span>
          </div>

          {/* Access Options for Non-Subscribers */}
          {!walletInfo.is_subscribed && (
            <div className="access-prompt">
              <div className="access-prompt-title">Unlock Premium Predictions</div>
              <div className="access-options-row">
                <button 
                  className="access-btn subscribe-btn"
                  onClick={() => setShowSubscription(true)}
                >
                  <IoCheckmarkCircle />
                  <div className="btn-content">
                    <span className="btn-title">Subscribe</span>
                    <span className="btn-desc">Unlock ALL • From R15</span>
                  </div>
                </button>
                <span className="or-divider">or</span>
                <button 
                  className="access-btn coins-btn"
                  onClick={() => setShowBuyCoins(true)}
                >
                  <IoWallet />
                  <div className="btn-content">
                    <span className="btn-title">Use Coins</span>
                    <span className="btn-desc">{COIN_COST_TIP} coins/game</span>
                  </div>
                </button>
              </div>
              <div className="access-balance">
                Your Balance: <strong>{walletInfo.balance.toLocaleString()} coins</strong>
              </div>
            </div>
          )}

          {Object.entries(premiumGrouped).map(([league, matches]) => (
            <CompetitionGroup 
              key={league}
              league={league}
              matches={matches.map(m => ({
                ...m,
                is_unlocked: walletInfo.is_subscribed || unlockedGames.has(m.id)
              }))}
              isFree={walletInfo.is_subscribed}
              onTipClick={(game) => {
                if (walletInfo.is_subscribed || unlockedGames.has(game.id)) {
                  handleTipClick(game)
                } else {
                  handleUnlockWithCoins(game)
                }
              }}
              isYesterday={false}
            />
          ))}
        </>
      )}

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

      {/* Tip Modal */}
      {selectedGame && (
        <TipModal 
          game={selectedGame} 
          onClose={() => setSelectedGame(null)} 
        />
      )}

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

      {/* WhatsApp Subscription Modal */}
      <WhatsAppSubscriptionModal
        isOpen={showWhatsAppModal}
        onClose={() => setShowWhatsAppModal(false)}
      />
    </div>
  )
}

export default GamesPage
