import React, { useState, useEffect } from 'react'
import { 
  IoTicket, IoRefresh, IoCopy, IoCheckmarkCircle, 
  IoFootball, IoTrophy, IoFlash, IoRocket,
  IoTime, IoStatsChart
} from 'react-icons/io5'

const API_URL = '/api'

const TICKET_CONFIGS = {
  'Build A Bet': {
    icon: IoFootball,
    color: '#10b981',
    bgGradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    description: 'Single game, multiple markets',
    oddsLabel: '1.90 - 3.40'
  },
  'Mixed Parlay': {
    icon: IoTrophy,
    color: '#f59e0b',
    bgGradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
    description: 'Multiple games combined',
    oddsLabel: '3.50 - 5.50'
  },
  'Big Odds': {
    icon: IoFlash,
    color: '#3b82f6',
    bgGradient: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
    description: 'Higher risk, max 12 games',
    oddsLabel: '8.00 - 25.00'
  },
  'Mega Odds': {
    icon: IoRocket,
    color: '#8b5cf6',
    bgGradient: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
    description: 'Jackpot potential, max 15 games',
    oddsLabel: '27.00 - 50.00'
  }
}

function AdminWhatsAppTicketsPage() {
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [generatedAt, setGeneratedAt] = useState(null)
  const [copiedId, setCopiedId] = useState(null)

  const fetchAllTickets = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`${API_URL}/admin/whatsapp-tickets`)
      const data = await response.json()
      
      if (data.error) {
        setError(data.error)
      } else {
        setTickets(data.tickets || [])
        setGeneratedAt(data.generated_at)
      }
    } catch (err) {
      console.error('Error fetching tickets:', err)
      setError('Failed to connect to server')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAllTickets()
  }, [])

  const formatTicketForCopy = (ticket) => {
    const config = TICKET_CONFIGS[ticket.type] || {}
    const date = new Date().toLocaleDateString('en-ZA', { 
      day: '2-digit', 
      month: 'short', 
      year: 'numeric' 
    })
    
    let text = `*${ticket.type}* - ${date}\n`
    text += `━━━━━━━━━━━━━━━━━\n`
    
    if (ticket.type === 'Build A Bet') {
      // Single game with multiple legs
      const match = ticket.match
      text += `*${match.home} vs ${match.away}*\n`
      text += `${match.league} | ${match.kickoff}\n\n`
      
      ticket.legs.forEach((leg, idx) => {
        text += `${idx + 1}. ${leg.selection} @ ${leg.odds}\n`
      })
    } else {
      // Multiple games
      ticket.legs.forEach((leg, idx) => {
        text += `${idx + 1}. ${leg.home} vs ${leg.away}\n`
        text += `   ${leg.selection} @ ${leg.odds}\n`
        if (idx < ticket.legs.length - 1) text += `\n`
      })
    }
    
    text += `\n━━━━━━━━━━━━━━━━━\n`
    text += `*Combined Odds:* ${ticket.combined_odds}\n`
    text += `*Confidence:* ${ticket.confidence}%\n`
    text += `\nGood luck!\n`
    
    return text
  }

  const copyToClipboard = async (ticket) => {
    const text = formatTicketForCopy(ticket)
    
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(ticket.id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
      // Fallback for older browsers
      const textarea = document.createElement('textarea')
      textarea.value = text
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopiedId(ticket.id)
      setTimeout(() => setCopiedId(null), 2000)
    }
  }

  const regenerateSingleTicket = async (ticketType) => {
    const endpoints = {
      'Build A Bet': 'build-a-bet',
      'Mixed Parlay': 'mixed-parlay',
      'Big Odds': 'big-odds',
      'Mega Odds': 'mega-odds'
    }
    
    const endpoint = endpoints[ticketType]
    if (!endpoint) return
    
    try {
      const response = await fetch(`${API_URL}/admin/whatsapp-tickets/${endpoint}`)
      const data = await response.json()
      
      if (data.ticket) {
        setTickets(prev => 
          prev.map(t => t.type === ticketType ? data.ticket : t)
        )
      }
    } catch (err) {
      console.error('Error regenerating ticket:', err)
    }
  }

  return (
    <div className="admin-tickets-page">
      <div className="admin-tickets-header">
        <div className="header-title">
          <IoTicket className="header-icon" />
          <div>
            <h1>WhatsApp Daily Tickets</h1>
            <p>Generate tickets for premium WhatsApp group</p>
          </div>
        </div>
        
        <button 
          className="refresh-all-btn"
          onClick={fetchAllTickets}
          disabled={loading}
        >
          <IoRefresh className={loading ? 'spinning' : ''} />
          {loading ? 'Generating...' : 'Regenerate All'}
        </button>
      </div>

      {generatedAt && (
        <div className="generated-timestamp">
          <IoTime /> Generated: {new Date(generatedAt).toLocaleString('en-ZA')}
        </div>
      )}

      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}

      <div className="tickets-grid">
        {tickets.map((ticket) => {
          const config = TICKET_CONFIGS[ticket.type] || {}
          const IconComponent = config.icon || IoTicket
          const isCopied = copiedId === ticket.id
          
          return (
            <div key={ticket.id} className="ticket-card">
              <div 
                className="ticket-header"
                style={{ background: config.bgGradient }}
              >
                <div className="ticket-type-info">
                  <IconComponent className="ticket-type-icon" />
                  <div>
                    <h3>{ticket.type}</h3>
                    <span className="odds-range">{config.oddsLabel}</span>
                  </div>
                </div>
                <div className="ticket-odds">
                  <span className="odds-value">{ticket.combined_odds}</span>
                  <span className="odds-label">odds</span>
                </div>
              </div>
              
              <div className="ticket-body">
                {ticket.type === 'Build A Bet' && ticket.match && (
                  <div className="single-match-header">
                    <strong>{ticket.match.home} vs {ticket.match.away}</strong>
                    <span className="match-league">{ticket.match.league}</span>
                    <span className="match-time">{ticket.match.kickoff}</span>
                  </div>
                )}
                
                <div className="ticket-legs">
                  {ticket.legs?.map((leg, idx) => (
                    <div key={idx} className="leg-item">
                      <span className="leg-number">{idx + 1}</span>
                      <div className="leg-details">
                        {ticket.type !== 'Build A Bet' && (
                          <span className="leg-match">{leg.home} vs {leg.away}</span>
                        )}
                        <span className="leg-selection">{leg.selection}</span>
                      </div>
                      <span className="leg-odds">@{leg.odds}</span>
                    </div>
                  ))}
                </div>
                
                <div className="ticket-stats">
                  <div className="stat-item">
                    <IoStatsChart />
                    <span>Confidence: {ticket.confidence}%</span>
                  </div>
                  {ticket.num_games && (
                    <div className="stat-item">
                      <IoFootball />
                      <span>{ticket.num_games} games</span>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="ticket-actions">
                <button 
                  className={`copy-btn ${isCopied ? 'copied' : ''}`}
                  onClick={() => copyToClipboard(ticket)}
                >
                  {isCopied ? (
                    <>
                      <IoCheckmarkCircle /> Copied!
                    </>
                  ) : (
                    <>
                      <IoCopy /> Copy for WhatsApp
                    </>
                  )}
                </button>
                <button 
                  className="regen-btn"
                  onClick={() => regenerateSingleTicket(ticket.type)}
                  title="Regenerate this ticket"
                >
                  <IoRefresh />
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {tickets.length === 0 && !loading && (
        <div className="no-tickets">
          <IoTicket />
          <p>No tickets generated yet</p>
          <button onClick={fetchAllTickets}>Generate Tickets</button>
        </div>
      )}

      <div className="admin-tickets-info">
        <h3>Ticket Types Explained:</h3>
        <ul>
          <li><strong>Build A Bet (1.90-3.40):</strong> Single game with 2-3 combined markets. Safest option.</li>
          <li><strong>Mixed Parlay (3.50-5.50):</strong> 3-4 different games combined. Balanced risk/reward.</li>
          <li><strong>Big Odds (8.00-25.00):</strong> Up to 12 games for bigger returns. Higher risk.</li>
          <li><strong>Mega Odds (27.00-50.00):</strong> Up to 15 games for jackpot potential. Highest risk.</li>
        </ul>
        <p className="info-note">Click &quot;Copy for WhatsApp&quot; to get formatted text ready to paste into your WhatsApp group.</p>
      </div>
    </div>
  )
}

export default AdminWhatsAppTicketsPage
