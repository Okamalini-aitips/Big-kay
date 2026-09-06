import React, { useState } from 'react'
import { IoSearch, IoCheckmarkCircle, IoCloseCircle, IoWarning, IoShield, IoTime, IoPerson, IoCash } from 'react-icons/io5'

const API_URL = '/api'

function AdminWhatsAppVerifyPage() {
  const [receiptId, setReceiptId] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [markingVerified, setMarkingVerified] = useState(false)

  const handleVerify = async () => {
    if (!receiptId.trim()) {
      alert('Please enter a Receipt ID')
      return
    }

    setLoading(true)
    setResult(null)

    try {
      const response = await fetch(`${API_URL}/admin/whatsapp/verify/${encodeURIComponent(receiptId.trim())}`)
      const data = await response.json()
      setResult(data)
    } catch (error) {
      console.error('Error verifying:', error)
      setResult({ valid: false, error: 'Failed to connect to server' })
    } finally {
      setLoading(false)
    }
  }

  const handleMarkVerified = async () => {
    if (!result?.receipt?.receipt_id) return

    setMarkingVerified(true)

    try {
      const response = await fetch(
        `${API_URL}/admin/whatsapp/mark-verified/${encodeURIComponent(result.receipt.receipt_id)}`,
        { method: 'POST' }
      )
      const data = await response.json()

      if (data.success) {
        setResult(prev => ({
          ...prev,
          already_verified: true,
          verified_at: data.verified_at
        }))
      } else {
        alert(data.error || 'Failed to mark as verified')
      }
    } catch (error) {
      console.error('Error marking verified:', error)
      alert('Failed to mark as verified')
    } finally {
      setMarkingVerified(false)
    }
  }

  const formatDate = (isoString) => {
    if (!isoString) return 'N/A'
    try {
      return new Date(isoString).toLocaleString('en-ZA', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return isoString
    }
  }

  return (
    <div className="admin-verify-page">
      <div className="admin-header">
        <IoShield className="admin-icon" />
        <h1>Receipt Verification</h1>
        <p>Verify WhatsApp Group subscription receipts</p>
      </div>

      <div className="verify-input-section">
        <label className="verify-label">Enter Receipt ID</label>
        <div className="verify-input-row">
          <input
            type="text"
            className="verify-input"
            placeholder="e.g., WA-20260821-E946C7A2"
            value={receiptId}
            onChange={(e) => setReceiptId(e.target.value.toUpperCase())}
            onKeyPress={(e) => e.key === 'Enter' && handleVerify()}
          />
          <button 
            className="verify-btn"
            onClick={handleVerify}
            disabled={loading}
          >
            {loading ? '...' : <IoSearch />}
          </button>
        </div>
      </div>

      {result && (
        <div className="verify-result">
          {result.valid ? (
            <>
              {result.already_verified ? (
                <div className="result-banner warning">
                  <IoWarning />
                  <span>ALREADY VERIFIED</span>
                </div>
              ) : (
                <div className="result-banner success">
                  <IoCheckmarkCircle />
                  <span>VALID RECEIPT</span>
                </div>
              )}

              <div className="receipt-details">
                <div className="detail-row">
                  <span className="detail-label">Receipt ID</span>
                  <span className="detail-value">{result.receipt.receipt_id}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">
                    <IoPerson /> Customer
                  </span>
                  <span className="detail-value">{result.receipt.user_name}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">
                    <IoCash /> Amount
                  </span>
                  <span className="detail-value highlight">R{result.receipt.amount}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">
                    <IoTime /> Purchased
                  </span>
                  <span className="detail-value">{formatDate(result.receipt.purchase_date)}</span>
                </div>
                <div className="detail-row">
                  <span className="detail-label">
                    <IoTime /> Valid Until
                  </span>
                  <span className="detail-value">{formatDate(result.receipt.valid_until)}</span>
                </div>
                {result.already_verified && (
                  <div className="detail-row verified-row">
                    <span className="detail-label">
                      <IoCheckmarkCircle /> Verified At
                    </span>
                    <span className="detail-value">{formatDate(result.verified_at)}</span>
                  </div>
                )}
              </div>

              {!result.already_verified && (
                <button 
                  className="mark-verified-btn"
                  onClick={handleMarkVerified}
                  disabled={markingVerified}
                >
                  {markingVerified ? 'Processing...' : 'Mark as Verified (Added to Group)'}
                </button>
              )}

              {result.already_verified && (
                <div className="already-verified-notice">
                  This receipt has already been verified. The user should already be in the group.
                </div>
              )}
            </>
          ) : (
            <>
              <div className="result-banner error">
                <IoCloseCircle />
                <span>INVALID RECEIPT</span>
              </div>
              <div className="error-message">
                {result.error || 'This receipt ID does not exist in our system. It may be fake or incorrectly typed.'}
              </div>
              <div className="error-tips">
                <strong>Tips:</strong>
                <ul>
                  <li>Double-check the Receipt ID for typos</li>
                  <li>Receipt IDs start with "WA-" followed by date and code</li>
                  <li>If suspicious, ask the user to show the full receipt</li>
                </ul>
              </div>
            </>
          )}
        </div>
      )}

      <div className="admin-info">
        <h3>How to use:</h3>
        <ol>
          <li>User sends you their receipt screenshot via WhatsApp</li>
          <li>Copy the Receipt ID from their receipt</li>
          <li>Paste it above and click verify</li>
          <li>If valid, add them to the group and click "Mark as Verified"</li>
          <li>If invalid or already used, do not add them</li>
        </ol>
      </div>
    </div>
  )
}

export default AdminWhatsAppVerifyPage
