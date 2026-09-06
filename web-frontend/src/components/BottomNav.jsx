import React from 'react'
import { NavLink } from 'react-router-dom'
import { IoHome, IoConstruct, IoLayers, IoTicket, IoSettings } from 'react-icons/io5'

function BottomNav() {
  return (
    <nav className="bottom-nav">
      <NavLink to="/games" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <IoHome />
        <span>Tips</span>
      </NavLink>
      <NavLink to="/build-a-bet" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <IoConstruct />
        <span>Build</span>
      </NavLink>
      <NavLink to="/mixed-markets" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <IoLayers />
        <span>Mixed</span>
      </NavLink>
      <NavLink to="/ticket-machine" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <IoTicket />
        <span>Machine</span>
      </NavLink>
      <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <IoSettings />
        <span>Settings</span>
      </NavLink>
    </nav>
  )
}

export default BottomNav
