import React, { useState } from 'react'
import { IoMenu } from 'react-icons/io5'
import { CoinWallet, BuyCoinsModal, SubscriptionModal, AccessOptionsModal } from './CoinWallet'

function Header() {
  const [showBuyCoins, setShowBuyCoins] = useState(false)
  const [showSubscription, setShowSubscription] = useState(false)
  const [showAccessOptions, setShowAccessOptions] = useState(false)
  const [walletKey, setWalletKey] = useState(0)

  const handlePurchaseComplete = () => {
    setWalletKey(prev => prev + 1) // Force wallet refresh
  }

  const handleAccessOption = (option) => {
    setShowAccessOptions(false)
    if (option === 'subscribe') {
      setShowSubscription(true)
    } else {
      setShowBuyCoins(true)
    }
  }

  return (
    <>
      <div className="header">
        <div className="header-left">
          <img 
            src="/images/okamoney-logo.webp" 
            alt="OkaMoney" 
            className="header-logo"
          />
          <span className="header-title">OkaMoney AI Tips</span>
        </div>
        <div className="header-right">
          <CoinWallet 
            key={walletKey}
            onOpenBuyCoins={() => setShowBuyCoins(true)} 
          />
        </div>
      </div>

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
    </>
  )
}

export default Header
