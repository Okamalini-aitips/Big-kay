import React, { useState, useEffect } from 'react'
import { IoWallet, IoAdd, IoClose, IoCheckmarkCircle, IoAlertCircle, IoTime } from 'react-icons/io5'

const API_URL = '/api'

function CoinWallet({ onOpenBuyCoins }) {
  const [balance, setBalance] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchBalance()
    // Refresh balance every 30 seconds
    const interval = setInterval(fetchBalance, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchBalance = async () => {
    try {
      const response = await fetch(`${API_URL}/wallet/balance`)
      const data = await response.json()
      setBalance(data.balance || 0)
    } catch (error) {
      console.error('Error fetching balance:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <button 
      className="coin-wallet-button"
      onClick={onOpenBuyCoins}
    >
      <IoWallet className="wallet-icon" />
      <span className="wallet-balance">{loading ? '...' : balance.toLocaleString()}</span>
      <IoAdd className="wallet-add-icon" />
    </button>
  )
}

// Buy Coins Modal Component
function BuyCoinsModal({ isOpen, onClose, onPurchaseComplete }) {
  const [packages, setPackages] = useState([])
  const [costs, setCosts] = useState({})
  const [disclaimer, setDisclaimer] = useState([])
  const [loading, setLoading] = useState(true)
  const [purchasing, setPurchasing] = useState(null)
  const [purchaseSuccess, setPurchaseSuccess] = useState(null)

  useEffect(() => {
    if (isOpen) {
      fetchPackages()
    }
  }, [isOpen])

  const fetchPackages = async () => {
    try {
      const response = await fetch(`${API_URL}/wallet/packages`)
      const data = await response.json()
      setPackages(data.packages || [])
      setCosts(data.costs || {})
      setDisclaimer(data.disclaimer?.lines || [])
    } catch (error) {
      console.error('Error fetching packages:', error)
    } finally {
      setLoading(false)
    }
  }

  const handlePurchase = async (packageId) => {
    setPurchasing(packageId)
    try {
      const response = await fetch(`${API_URL}/wallet/purchase?package_id=${packageId}`, {
        method: 'POST'
      })
      const data = await response.json()
      
      if (data.success) {
        setPurchaseSuccess({
          coins: data.coins_added,
          balance: data.new_balance
        })
        if (onPurchaseComplete) {
          onPurchaseComplete(data.new_balance)
        }
        // Auto close after 2 seconds
        setTimeout(() => {
          setPurchaseSuccess(null)
          onClose()
        }, 2000)
      }
    } catch (error) {
      console.error('Error purchasing coins:', error)
    } finally {
      setPurchasing(null)
    }
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="buy-coins-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">
            <IoWallet style={{ color: '#c19a49' }} />
            Buy Coins
          </h2>
          <button className="modal-close" onClick={onClose}>
            <IoClose />
          </button>
        </div>

        {purchaseSuccess ? (
          <div className="purchase-success">
            <IoCheckmarkCircle className="success-icon" />
            <div className="success-title">Purchase Successful!</div>
            <div className="success-coins">+{purchaseSuccess.coins.toLocaleString()} coins</div>
            <div className="success-balance">New Balance: {purchaseSuccess.balance.toLocaleString()}</div>
          </div>
        ) : (
          <>
            <div className="modal-body">
              <div className="coin-packages">
                {packages.map(pkg => (
                  <div 
                    key={pkg.id} 
                    className={`coin-package ${pkg.featured ? 'featured' : ''}`}
                  >
                    {pkg.featured && <div className="package-badge">MOST POPULAR</div>}
                    <div className="package-coins">{pkg.label}</div>
                    {pkg.bonus && (
                      <div className="package-bonus">+{pkg.bonus} bonus</div>
                    )}
                    <div className="package-price">R{pkg.price}</div>
                    <div className="package-description">{pkg.description}</div>
                    <button 
                      className="package-buy-btn"
                      onClick={() => handlePurchase(pkg.id)}
                      disabled={purchasing === pkg.id}
                    >
                      {purchasing === pkg.id ? 'Processing...' : 'Buy Now'}
                    </button>
                  </div>
                ))}
              </div>

              <div className="coin-usage-info">
                <h4>How to use your coins:</h4>
                <ul className="usage-list">
                  <li><span className="usage-cost">{costs.view_tip} coins</span> to view a game prediction</li>
                  <li><span className="usage-cost">{costs.build_a_bet} coins</span> to unlock a Build A Bet ticket</li>
                  <li><span className="usage-cost">{costs.mixed_parlay} coins</span> to unlock a Mixed Parlay ticket</li>
                  <li><span className="usage-cost">{costs.ticket_machine} coins</span> to generate a Ticket Machine betslip</li>
                </ul>
              </div>
            </div>

            <div className="disclaimer-section">
              <IoAlertCircle className="disclaimer-icon" />
              <div className="disclaimer-content">
                <div className="disclaimer-title">Important Notice</div>
                <ul className="disclaimer-list">
                  {disclaimer.map((line, i) => (
                    <li key={i}>{line}</li>
                  ))}
                </ul>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// Subscription Modal Component
function SubscriptionModal({ isOpen, onClose, onSubscribeComplete }) {
  const [subscribing, setSubscribing] = useState(null)
  const [success, setSuccess] = useState(false)

  const plans = [
    { id: '1day', days: 1, price: 15, label: '1 Day' },
    { id: '7days', days: 7, price: 85, label: '7 Days', featured: true },
    { id: '30days', days: 30, price: 180, label: '30 Days' }
  ]

  const handleSubscribe = async (plan) => {
    setSubscribing(plan.id)
    try {
      const response = await fetch(`${API_URL}/wallet/subscribe?is_subscribed=true&days=${plan.days}`, {
        method: 'POST'
      })
      const data = await response.json()
      
      if (data.success) {
        setSuccess(true)
        if (onSubscribeComplete) {
          onSubscribeComplete()
        }
        setTimeout(() => {
          setSuccess(false)
          onClose()
        }, 2000)
      }
    } catch (error) {
      console.error('Error subscribing:', error)
    } finally {
      setSubscribing(null)
    }
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="subscription-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">
            <IoCheckmarkCircle style={{ color: '#16a34a' }} />
            Subscribe
          </h2>
          <button className="modal-close" onClick={onClose}>
            <IoClose />
          </button>
        </div>

        {success ? (
          <div className="purchase-success">
            <IoCheckmarkCircle className="success-icon" />
            <div className="success-title">Subscribed!</div>
            <div className="success-coins">All premium content unlocked</div>
          </div>
        ) : (
          <div className="modal-body">
            <div className="subscription-benefits">
              <h4>Subscriber Benefits:</h4>
              <ul className="benefits-list">
                <li><IoCheckmarkCircle /> Access to ALL daily predictions</li>
                <li><IoCheckmarkCircle /> 1 FREE Build A Bet ticket daily</li>
                <li><IoCheckmarkCircle /> 1 FREE Mixed Parlay ticket daily</li>
                <li><IoCheckmarkCircle /> 1 FREE Ticket Machine betslip daily</li>
                <li><IoCheckmarkCircle /> Save your coins for extra picks!</li>
              </ul>
            </div>

            <div className="subscription-plans">
              {plans.map(plan => (
                <div 
                  key={plan.id} 
                  className={`subscription-plan ${plan.featured ? 'featured' : ''}`}
                >
                  {plan.featured && <div className="plan-badge">POPULAR</div>}
                  <div className="plan-duration">{plan.label}</div>
                  <div className="plan-price">R{plan.price}</div>
                  <button 
                    className="plan-subscribe-btn"
                    onClick={() => handleSubscribe(plan)}
                    disabled={subscribing === plan.id}
                  >
                    {subscribing === plan.id ? 'Processing...' : 'Subscribe'}
                  </button>
                </div>
              ))}
            </div>

            <div className="subscription-note">
              <IoTime />
              <span>Subscription starts immediately upon payment confirmation</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Combined Access Options Modal
function AccessOptionsModal({ isOpen, onClose, onSelectOption }) {
  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="access-options-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Unlock Premium Content</h2>
          <button className="modal-close" onClick={onClose}>
            <IoClose />
          </button>
        </div>

        <div className="modal-body">
          <div className="access-options">
            <button 
              className="access-option subscribe-option"
              onClick={() => onSelectOption('subscribe')}
            >
              <div className="option-icon">
                <IoCheckmarkCircle />
              </div>
              <div className="option-content">
                <div className="option-title">Subscribe</div>
                <div className="option-description">
                  Unlock ALL predictions + FREE daily tickets
                </div>
                <div className="option-pricing">From R15/day</div>
              </div>
            </button>

            <div className="option-divider">
              <span>OR</span>
            </div>

            <button 
              className="access-option coins-option"
              onClick={() => onSelectOption('coins')}
            >
              <div className="option-icon">
                <IoWallet />
              </div>
              <div className="option-content">
                <div className="option-title">Buy Coins</div>
                <div className="option-description">
                  Pay per prediction or ticket as you go
                </div>
                <div className="option-pricing">From R50 for 500 coins</div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export { CoinWallet, BuyCoinsModal, SubscriptionModal, AccessOptionsModal }
export default CoinWallet
