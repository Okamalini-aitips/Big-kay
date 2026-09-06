import React, { createContext, useContext, useState, useEffect } from 'react'

const API_URL = '/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)

  // Load token from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('okamoney_token')
    const savedUser = localStorage.getItem('okamoney_user')
    
    if (savedToken && savedUser) {
      setToken(savedToken)
      setUser(JSON.parse(savedUser))
    }
    setLoading(false)
  }, [])

  // Save token to localStorage when it changes
  useEffect(() => {
    if (token) {
      localStorage.setItem('okamoney_token', token)
    } else {
      localStorage.removeItem('okamoney_token')
    }
  }, [token])

  // Save user to localStorage when it changes
  useEffect(() => {
    if (user) {
      localStorage.setItem('okamoney_user', JSON.stringify(user))
    } else {
      localStorage.removeItem('okamoney_user')
    }
  }, [user])

  const register = async (email, password, name = '') => {
    try {
      const response = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name })
      })
      
      const data = await response.json()
      
      if (!response.ok) {
        return { success: false, error: data.detail || 'Registration failed' }
      }
      
      setToken(data.token)
      setUser(data.user)
      
      return { success: true, user: data.user }
    } catch (error) {
      console.error('Register error:', error)
      return { success: false, error: 'Network error. Please try again.' }
    }
  }

  const login = async (email, password) => {
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      
      const data = await response.json()
      
      if (!response.ok) {
        return { success: false, error: data.detail || 'Login failed' }
      }
      
      setToken(data.token)
      setUser(data.user)
      
      return { success: true, user: data.user }
    } catch (error) {
      console.error('Login error:', error)
      return { success: false, error: 'Network error. Please try again.' }
    }
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    localStorage.removeItem('okamoney_token')
    localStorage.removeItem('okamoney_user')
  }

  const getAuthHeader = () => {
    if (token) {
      return { 'Authorization': `Bearer ${token}` }
    }
    return {}
  }

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!token,
    register,
    login,
    logout,
    getAuthHeader
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default AuthContext
