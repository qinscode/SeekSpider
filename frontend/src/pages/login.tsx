import { useQuery } from '@tanstack/react-query'
import React, { SVGProps, useState } from 'react'

import { getApiUrl, getAuthProviders, login } from '@/repository'
import MicrosoftIcon from '@/components/icons/microsoft'
import GoogleIcon from '@/components/icons/google'

const ICONS: Record<string, React.FC<SVGProps<SVGSVGElement>>> = {
  google: GoogleIcon,
  microsoft: MicrosoftIcon,
}

const LoginPage: React.FC = () => {
  const providersQuery = useQuery(getAuthProviders())
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      await login(email, password)
      // Redirect to home page after successful login
      window.location.href = '/'
    } catch (err: any) {
      setError(err.message || 'Invalid email or password')
    } finally {
      setIsLoading(false)
    }
  }

  const hasCredentialsProvider = providersQuery.data?.some(
    (p) => p.id === 'supabase' || (p as any).type === 'credentials'
  )
  const hasOAuthProviders = providersQuery.data?.some(
    (p) => p.id !== 'supabase' && (p as any).type !== 'credentials'
  )

  return (
    <div className="min-h-screen flex justify-center items-center bg-[#0a0e17] relative overflow-hidden font-sans text-gray-300">
      {/* Background Pattern */}
      <div
        className="absolute inset-0 z-0"
        style={{
          backgroundImage: `linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px)`,
          backgroundSize: '30px 30px',
        }}
      />
      
      {/* Neon Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-neon-500/10 rounded-full blur-[100px] pointer-events-none"></div>

      <div className="glass-panel w-full max-w-md p-8 rounded-2xl shadow-glass relative z-10 mx-4">
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 bg-dark-900/50 rounded-full flex items-center justify-center mb-4 border border-white/10 shadow-[0_0_15px_rgba(6,182,212,0.2)]">
            <img src="/logo.svg" alt="Plombery logo" className="w-10 h-10" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Welcome to Plombery
          </h1>
          <p className="text-sm text-gray-500 mt-2">Sign in to access your pipelines</p>
        </div>

        {hasCredentialsProvider && (
          <form onSubmit={handleSubmit} className="space-y-5 mb-6">
            <div>
              <label
                htmlFor="email"
                className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                disabled={isLoading}
                className="w-full bg-dark-950/50 border border-gray-800 rounded-lg px-4 py-2.5 text-gray-200 placeholder-gray-600 focus:outline-none focus:border-neon-500/50 focus:ring-1 focus:ring-neon-500/50 transition-all"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                disabled={isLoading}
                className="w-full bg-dark-950/50 border border-gray-800 rounded-lg px-4 py-2.5 text-gray-200 placeholder-gray-600 focus:outline-none focus:border-neon-500/50 focus:ring-1 focus:ring-neon-500/50 transition-all"
              />
            </div>

            {error && (
              <div className="bg-red-950/30 border border-red-500/30 text-red-400 text-sm px-4 py-2 rounded-lg">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-neon-600 hover:bg-neon-500 text-white font-semibold py-2.5 rounded-lg transition-all shadow-[0_0_15px_rgba(6,182,212,0.3)] hover:shadow-[0_0_20px_rgba(6,182,212,0.5)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
        )}

        {hasCredentialsProvider && hasOAuthProviders && (
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-800"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-[#111827] text-gray-500">
                Or continue with
              </span>
            </div>
          </div>
        )}

        <div className="space-y-3">
          {providersQuery.data
            ?.filter((p) => p.id !== 'supabase' && (p as any).type !== 'credentials')
            .map((provider) => {
              const Icon = ICONS[provider.id]

              return (
                <a
                  key={provider.name}
                  href={`${getApiUrl()}/auth/login`}
                  className="flex items-center justify-center gap-3 w-full bg-dark-900/50 hover:bg-dark-800 border border-gray-800 hover:border-gray-700 text-gray-300 font-medium py-2.5 rounded-lg transition-all no-underline"
                >
                  {Icon && <Icon className="fill-current w-5 h-5" />}
                  Sign in with {provider.name}
                </a>
              )
            })}
        </div>
      </div>
    </div>
  )
}

export default LoginPage
