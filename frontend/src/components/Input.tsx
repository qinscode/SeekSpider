import React, { forwardRef } from 'react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  icon?: React.ReactNode
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, icon, className = '', ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-sm font-medium text-gray-400 mb-1.5">
            {label}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            className={`
              w-full bg-[#111827]/50 border border-white/5 rounded-lg px-4 py-2.5 text-sm text-gray-200 font-mono
              placeholder-gray-600 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 
              focus:shadow-[0_0_15px_rgba(34,211,238,0.15)] transition-all
              ${error ? 'border-red-500/50 focus:border-red-500/50 focus:ring-red-500/50' : ''}
              ${icon ? 'pl-10' : ''}
              ${className}
            `}
            {...props}
          />
          {icon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none">
              {icon}
            </div>
          )}
        </div>
        {error && <p className="mt-1 text-xs text-rose-400">{error}</p>}
      </div>
    )
  }
)

Input.displayName = 'Input'

export default Input
