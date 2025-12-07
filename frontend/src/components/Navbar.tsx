import React, { ReactNode } from 'react'
import { Link } from 'react-router'
import SettingsMenu from './SettingsMenu'

interface NavbarProps {
  children?: ReactNode
  className?: string
}

const Navbar: React.FC<NavbarProps> = ({ children, className = '' }) => {
  return (
    <header className={`px-8 py-4 glass-panel border-b-0 z-20 relative shrink-0 flex flex-col gap-4 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400 tracking-tight drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]">
              Plombery
            </h1>
          </Link>
        </div>

        <div className="flex items-center gap-5">
          <SettingsMenu />
        </div>
      </div>
      
      {children && (
        <div className="w-full">
          {children}
        </div>
      )}
    </header>
  )
}

export default Navbar
