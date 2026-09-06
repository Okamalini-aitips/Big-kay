import React, { useState, useEffect, useRef } from 'react'
import { IoClose, IoLogoWhatsapp, IoLockClosed, IoTime, IoCheckmarkCircle, IoDownload, IoShare } from 'react-icons/io5'

const API_URL = '/api'

function WhatsAppSubscriptionModal({ isOpen, onClose }) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [purchasing, setPurchasing] = useState(false)
  const [receipt, setReceipt] = useState(null)
  const [userName, setUserName] = useState('')
  const receiptRef = useRef(null)

  useEffect(() => {
    if (isOpen) {
      fetchStatus()
    }
  }, [isOpen])

  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/whatsapp/status`)
      const data = await response.json()
      setStatus(data)
    } catch (error) {
      console.error('Error fetching WhatsApp status:', error)
    } finally {
      setLoading(false)
    }
  }

  const handlePurchase = async () => {
    if (!userName.trim()) {
      alert('Please enter your name for the receipt')
      return
    }
    
    setPurchasing(true)
    try {
      const response = await fetch(
        `${API_URL}/whatsapp/purchase?user_name=${encodeURIComponent(userName)}`,
        { method: 'POST' }
      )
      const data = await response.json()
      
      if (data.success) {
        setReceipt(data.receipt)
      } else {
        alert(data.error || 'Purchase failed')
      }
    } catch (error) {
      console.error('Error purchasing:', error)
      alert('Purchase failed. Please try again.')
    } finally {
      setPurchasing(false)
    }
  }

  const handleDownloadReceipt = () => {
    if (!receipt) return
    
    const receiptText = `
╔══════════════════════════════════════════════════════════╗
║            OKAMONEY AI TIPS - PAYMENT RECEIPT            ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Receipt ID: ${receipt.receipt_id.padEnd(38)}║
║                                                          ║
║  Customer: ${receipt.user_name.padEnd(40)}║
║                                                          ║
║  Product: WhatsApp Group Subscription                    ║
║                                                          ║
║  Amount Paid: R${receipt.amount}                                    ║
║                                                          ║
║  Purchase Date: ${receipt.purchase_date.padEnd(34)}║
║  Purchase Time: ${receipt.purchase_time.padEnd(34)}║
║                                                          ║
║  Valid Until: ${receipt.valid_until.padEnd(36)}║
║                                                          ║
║  Status: ✓ PAID                                          ║
║                                                          ║
╠══════════════════════════════════════════════════════════╣
║                     HOW TO JOIN                          ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  1. Screenshot or save this receipt                      ║
║  2. Send to WhatsApp: +27 72 517 7829                    ║
║  3. You will be added to the premium tips group          ║
║                                                          ║
╠══════════════════════════════════════════════════════════╣
║     Thank you for your purchase! - OkaMoney AI Tips      ║
╚══════════════════════════════════════════════════════════╝
    `.trim()
    
    const blob = new Blob([receiptText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `OkaMoney_Receipt_${receipt.receipt_id}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleShareToWhatsApp = () => {
    if (!receipt) return
    
    const message = `Hi OkaMoney! I just purchased the WhatsApp Group Subscription.\n\nReceipt ID: ${receipt.receipt_id}\nName: ${receipt.user_name}\nAmount: R${receipt.amount}\nDate: ${receipt.purchase_date}\n\nPlease add me to the premium tips group. Thank you!`
    
    const whatsappUrl = `https://wa.me/27725177829?text=${encodeURIComponent(message)}`
    window.open(whatsappUrl, '_blank')
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="whatsapp-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header whatsapp-header">
          <h2 className="modal-title">
            <IoLogoWhatsapp style={{ color: '#25D366' }} />
            WhatsApp Group
          </h2>
          <button className="modal-close" onClick={onClose}>
            <IoClose />
          </button>
        </div>

        {loading ? (
          <div className="modal-loading">
            <div className="spinner"></div>
            <span>Loading...</span>
          </div>
        ) : receipt ? (
          // Receipt View
          <div className="receipt-view">
            <div className="receipt-success-banner">
              <IoCheckmarkCircle />
              <span>Payment Successful!</span>
            </div>
            
            <div className="receipt-card" ref={receiptRef}>
              <div className="receipt-header">
                <div className="receipt-logo">OkaMoney AI Tips</div>
                <div className="receipt-title">PAYMENT RECEIPT</div>
              </div>
              
              <div className="receipt-body">
                <div className="receipt-row">
                  <span className="receipt-label">Receipt ID</span>
                  <span className="receipt-value">{receipt.receipt_id}</span>
                </div>
                <div className="receipt-row">
                  <span className="receipt-label">Customer</span>
                  <span className="receipt-value">{receipt.user_name}</span>
                </div>
                <div className="receipt-row">
                  <span className="receipt-label">Product</span>
                  <span className="receipt-value">WhatsApp Group</span>
                </div>
                <div className="receipt-row highlight">
                  <span className="receipt-label">Amount Paid</span>
                  <span className="receipt-value">R{receipt.amount}</span>
                </div>
                <div className="receipt-row">
                  <span className="receipt-label">Date</span>
                  <span className="receipt-value">{receipt.purchase_date}</span>
                </div>
                <div className="receipt-row">
                  <span className="receipt-label">Valid Until</span>
                  <span className="receipt-value">{receipt.valid_until}</span>
                </div>
                <div className="receipt-status">
                  <IoCheckmarkCircle /> PAID
                </div>
              </div>
            </div>
            
            <div className="receipt-instructions">
              <div className="instruction-title">Next Steps:</div>
              <ol className="instruction-list">
                <li>Download or screenshot this receipt</li>
                <li>Send it to our WhatsApp</li>
                <li>Get added to the premium tips group!</li>
              </ol>
            </div>
            
            <div className="receipt-actions">
              <button className="receipt-btn download" onClick={handleDownloadReceipt}>
                <IoDownload />
                Download Receipt
              </button>
              <button className="receipt-btn whatsapp" onClick={handleShareToWhatsApp}>
                <IoLogoWhatsapp />
                Send to WhatsApp
              </button>
            </div>
          </div>
        ) : status?.is_open ? (
          // Purchase Window Open
          <div className="modal-body">
            <div className="whatsapp-open-banner">
              <IoCheckmarkCircle />
              <span>Purchase Window is OPEN!</span>
            </div>
            
            <div className="whatsapp-product">
              <div className="product-icon">
                <IoLogoWhatsapp />
              </div>
              <div className="product-info">
                <div className="product-name">Premium WhatsApp Group</div>
                <div className="product-desc">Daily betting tips delivered to your phone</div>
              </div>
              <div className="product-price">R{status.price}</div>
            </div>
            
            <div className="whatsapp-benefits">
              <div className="benefit-item">
                <IoCheckmarkCircle />
                <span>2-4 premium betslips daily</span>
              </div>
              <div className="benefit-item">
                <IoCheckmarkCircle />
                <span>1.90-5.50 odds range</span>
              </div>
              <div className="benefit-item">
                <IoCheckmarkCircle />
                <span>Direct to your WhatsApp</span>
              </div>
              <div className="benefit-item">
                <IoCheckmarkCircle />
                <span>Valid for ~30 days from purchase</span>
              </div>
            </div>
            
            <div className="purchase-form">
              <label className="form-label">Your Name (for receipt)</label>
              <input
                type="text"
                className="form-input"
                placeholder="Enter your name"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
              />
            </div>
            
            <button 
              className="whatsapp-purchase-btn"
              onClick={handlePurchase}
              disabled={purchasing || !userName.trim()}
            >
              {purchasing ? 'Processing...' : `Pay R${status.price} Now`}
            </button>
            
            <div className="whatsapp-note">
              After payment, you'll receive a receipt to send to our WhatsApp for group access.
            </div>
          </div>
        ) : (
          // Purchase Window Closed
          <div className="modal-body">
            <div className="whatsapp-closed-banner">
              <IoLockClosed />
              <span>Purchase Window Closed</span>
            </div>
            
            <div className="whatsapp-countdown-section">
              <div className="countdown-title">Next window opens on</div>
              <div className="countdown-date">{status?.next_window_formatted}</div>
              
              <div className="countdown-timer">
                <div className="countdown-item">
                  <span className="countdown-value">{status?.countdown?.days || 0}</span>
                  <span className="countdown-label">Days</span>
                </div>
                <div className="countdown-separator">:</div>
                <div className="countdown-item">
                  <span className="countdown-value">{status?.countdown?.hours || 0}</span>
                  <span className="countdown-label">Hours</span>
                </div>
                <div className="countdown-separator">:</div>
                <div className="countdown-item">
                  <span className="countdown-value">{status?.countdown?.minutes || 0}</span>
                  <span className="countdown-label">Mins</span>
                </div>
              </div>
            </div>
            
            <div className="whatsapp-schedule">
              <div className="schedule-title">Purchase Windows</div>
              <div className="schedule-info">
                <div className="schedule-row">
                  <IoTime />
                  <span><strong>8th</strong> of every month</span>
                </div>
                <div className="schedule-row">
                  <IoTime />
                  <span><strong>26th</strong> of every month</span>
                </div>
              </div>
              <div className="schedule-note">
                Groups start on these dates to ensure quality service and manageable group sizes.
              </div>
            </div>
            
            <div className="whatsapp-price-preview">
              <span>WhatsApp Group Subscription</span>
              <span className="price">R{status?.price}/month</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default WhatsAppSubscriptionModal
