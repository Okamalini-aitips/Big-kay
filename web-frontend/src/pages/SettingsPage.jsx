import React from 'react'
import Header from '../components/Header'
import { IoCog, IoStatsChart, IoPricetag, IoInformationCircle } from 'react-icons/io5'

function SettingsPage() {
  return (
    <div className="page-content">
      <Header />
      
      <div className="settings-page">
        <div className="settings-title">Settings</div>
        
        {/* Daily Output */}
        <div className="settings-section">
          <div className="settings-section-header">
            <IoStatsChart className="settings-section-icon" />
            <span>Daily Output</span>
          </div>
          <div className="settings-section-content">
            <div className="output-row">
              <span className="output-label">100 Games</span>
              <span className="output-value">3 free / 97 premium</span>
            </div>
            <div className="output-row">
              <span className="output-label">Build A Bet</span>
              <span className="output-value">2 betslips</span>
            </div>
            <div className="output-row">
              <span className="output-label">Mixed Markets</span>
              <span className="output-value">3 betslips</span>
            </div>
            <div className="output-row">
              <span className="output-label">Ticket Machine</span>
              <span className="output-value">1 free + 4 purchasable</span>
            </div>
          </div>
        </div>
        
        {/* Subscription Plans */}
        <div className="settings-section">
          <div className="settings-section-header">
            <IoPricetag className="settings-section-icon" />
            <span>Subscription Plans</span>
          </div>
          <div className="settings-section-content">
            <div className="pricing-row">
              <span className="pricing-name">1 Day Access</span>
              <span className="pricing-amount">R15</span>
            </div>
            <div className="pricing-row">
              <span className="pricing-name">7 Day Access</span>
              <span className="pricing-amount">R85</span>
            </div>
            <div className="pricing-row">
              <span className="pricing-name">30 Day Access</span>
              <span className="pricing-amount">R180</span>
            </div>
            <div className="pricing-row">
              <span className="pricing-name">Ticket Bundle (4 tickets)</span>
              <span className="pricing-amount">R15</span>
            </div>
            <div className="coming-soon-text">Payfast Integration Coming Soon</div>
          </div>
        </div>
        
        {/* Algorithm Info */}
        <div className="settings-section">
          <div className="settings-section-header">
            <IoCog className="settings-section-icon" />
            <span>Algorithm</span>
          </div>
          <div className="settings-section-content">
            <p style={{ marginBottom: '12px' }}>
              OkaMoney AI Tips uses advanced statistical analysis across 13 betting markets:
            </p>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.8', fontSize: '12px' }}>
              <li>Both Teams To Score (BTTS)</li>
              <li>Over/Under Goals (0.5 - 4.5)</li>
              <li>Double Chance</li>
              <li>Corners (Over/Under)</li>
              <li>Cards (Over/Under)</li>
              <li>Straight Win (Home/Away)</li>
              <li>Half-Time Results</li>
            </ul>
          </div>
        </div>
        
        {/* About */}
        <div className="settings-section">
          <div className="settings-section-header">
            <IoInformationCircle className="settings-section-icon" />
            <span>About</span>
          </div>
          <div className="settings-section-content">
            <p>
              OkaMoney AI Tips provides AI-powered sports betting predictions for informational purposes. 
              Our algorithm analyzes team form, head-to-head records, league positions, and historical data 
              to generate daily picks.
            </p>
            <p style={{ marginTop: '12px', color: '#f59e0b', fontWeight: '600' }}>
              Please gamble responsibly. 18+ only.
            </p>
          </div>
        </div>
      </div>
      
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
    </div>
  )
}

export default SettingsPage
