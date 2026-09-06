import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import BottomNav from './components/BottomNav'
import GamesPage from './pages/GamesPage'
import BuildABetPage from './pages/BuildABetPage'
import MixedMarketsPage from './pages/MixedMarketsPage'
import TicketMachinePage from './pages/TicketMachinePage'
import SettingsPage from './pages/SettingsPage'
import AdminCardsPage from './pages/AdminCardsPage'
import AdminWhatsAppVerifyPage from './pages/AdminWhatsAppVerifyPage'
import AdminWhatsAppTicketsPage from './pages/AdminWhatsAppTicketsPage'
import AdminResultsPage from './pages/AdminResultsPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="container">
          <Routes>
            <Route path="/" element={<Navigate to="/games" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/games" element={<GamesPage />} />
            <Route path="/build-a-bet" element={<BuildABetPage />} />
            <Route path="/mixed-markets" element={<MixedMarketsPage />} />
            <Route path="/ticket-machine" element={<TicketMachinePage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/admin/cards" element={<AdminCardsPage />} />
            <Route path="/admin/verify" element={<AdminWhatsAppVerifyPage />} />
            <Route path="/admin/whatsapp-tickets" element={<AdminWhatsAppTicketsPage />} />
            <Route path="/admin/results" element={<AdminResultsPage />} />
          </Routes>
          <BottomNav />
        </div>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
