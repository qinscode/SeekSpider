
import {
  Cog6ToothIcon,
  MoonIcon,
  SunIcon,
  ComputerDesktopIcon,
  CodeBracketSquareIcon,
  ArrowTopRightOnSquareIcon,
  ArchiveBoxIcon,
  BookOpenIcon,
  KeyIcon,
} from '@heroicons/react/24/outline'
import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { useAuthState } from '@/contexts/AuthContext'
import { getApiUrl, getLatestRelease } from '@/repository'
import { Popover, PopoverContent, PopoverTrigger } from './Popover'
import UserInfo from './UserInfo'
import { version } from '../../package.json'

interface Props {}

const THEME_MODE_LIGHT = 0
const THEME_MODE_DARK = 1
const THEME_MODE_AUTO = 2
const THEME_MODES: Record<number, 'light' | 'dark'> = {
  [THEME_MODE_LIGHT]: 'light',
  [THEME_MODE_DARK]: 'dark',
}
const THEME_LOCAL_STORAGE_KEY = 'plomberyTheme'

const ThemeSwitch: React.FC = () => {
  const initialMode =
    localStorage[THEME_LOCAL_STORAGE_KEY] === 'dark'
      ? THEME_MODE_DARK
      : THEME_LOCAL_STORAGE_KEY in localStorage
      ? THEME_MODE_LIGHT
      : THEME_MODE_AUTO
  const [themeMode, setThemeMode] = useState(initialMode)

  const handleThemeChange = (i: number) => {
    let isDarkMode = false

    if (i === THEME_MODE_AUTO) {
      localStorage.removeItem(THEME_LOCAL_STORAGE_KEY)
      isDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches
    } else {
      isDarkMode = i === THEME_MODE_DARK
      localStorage[THEME_LOCAL_STORAGE_KEY] = THEME_MODES[i]
    }

    if (isDarkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }

    setThemeMode(i)
  }

  return (
    <div className="flex bg-dark-950/50 p-1 rounded-lg border border-white/5">
      <button
        onClick={() => handleThemeChange(THEME_MODE_LIGHT)}
        className={`flex-1 flex items-center justify-center gap-2 py-1.5 rounded-md text-xs font-medium transition-all ${
          themeMode === THEME_MODE_LIGHT
            ? 'bg-gray-700 text-white shadow-sm'
            : 'text-gray-500 hover:text-gray-300'
        }`}
      >
        <SunIcon className="w-4 h-4" />
        Light
      </button>
      <button
        onClick={() => handleThemeChange(THEME_MODE_DARK)}
        className={`flex-1 flex items-center justify-center gap-2 py-1.5 rounded-md text-xs font-medium transition-all ${
          themeMode === THEME_MODE_DARK
            ? 'bg-gray-700 text-white shadow-sm'
            : 'text-gray-500 hover:text-gray-300'
        }`}
      >
        <MoonIcon className="w-4 h-4" />
        Dark
      </button>
      <button
        onClick={() => handleThemeChange(THEME_MODE_AUTO)}
        className={`flex-1 flex items-center justify-center gap-2 py-1.5 rounded-md text-xs font-medium transition-all ${
          themeMode === THEME_MODE_AUTO
            ? 'bg-gray-700 text-white shadow-sm'
            : 'text-gray-500 hover:text-gray-300'
        }`}
      >
        <ComputerDesktopIcon className="w-4 h-4" />
        System
      </button>
    </div>
  )
}

const isNewerReleaseAvailable = (current: string, latest: string): boolean => {
  const currentParts = current.replace(/^v/, '').split('.').map(Number)
  const latestParts = latest.replace(/^v/, '').split('.').map(Number)

  for (let i = 0; i < currentParts.length; i++) {
    if (currentParts[i] > latestParts[i]) {
      return false
    } else if (currentParts[i] < latestParts[i]) {
      return true
    }
  }

  return false
}

const SettingsMenu: React.FC<Props> = () => {
  const [isOpen, setOpen] = useState(false)
  const { user, isAuthenticationEnabled } = useAuthState()
  const ghLatestRelease = useQuery({ ...getLatestRelease(), enabled: isOpen })

  // If auth is not enabled, just show a settings icon
  let dialogTrigger: React.ReactElement | string = <Cog6ToothIcon />

  // otherwise show the user's avatar
  if (isAuthenticationEnabled && user) {
    const emailInitial = user.email?.trim().charAt(0)?.toUpperCase()
    dialogTrigger = emailInitial || user.name?.charAt(0) || '?'
  }

  const isNewerRelease = ghLatestRelease.isSuccess
    ? isNewerReleaseAvailable(version, ghLatestRelease.data.tag_name)
    : false

  return (
    <Popover placement="bottom-end" open={isOpen} onOpenChange={setOpen}>
      <PopoverTrigger onClick={() => setOpen(true)}>
        <div
          className="flex justify-center items-center font-medium bg-dark-800/50 border border-white/10 text-indigo-400 rounded-full hover:border-indigo-500/50 hover:text-indigo-300 hover:shadow-[0_0_15px_rgba(99,102,241,0.3)] transition-all cursor-pointer"
          style={{ width: 34, height: 34 }}
        >
          {typeof dialogTrigger === 'string' ? (
            <span className="text-sm">{dialogTrigger}</span>
          ) : (
            <span className="w-5 h-5">{dialogTrigger}</span>
          )}
        </div>
      </PopoverTrigger>
      <PopoverContent>
        <div className="glass-panel rounded-xl shadow-glass overflow-hidden min-w-[280px] py-2 backdrop-blur-xl bg-dark-900/90 border border-white/10">
          {isAuthenticationEnabled && (
            <>
              <div className="pt-2">
                <UserInfo />
              </div>
              <div className="h-px bg-white/5 mx-4 mb-2" />
            </>
          )}

          <div className="flex flex-col">
            <Link
              className="flex items-center px-6 py-2.5 text-sm text-gray-300 hover:bg-white/5 hover:text-white transition-colors gap-3"
              to="/settings/tokens"
              onClick={() => setOpen(false)}
            >
              <KeyIcon className="w-4 h-4 text-gray-500" />
              <span className="flex-grow">API Tokens</span>
            </Link>

            <a
              className="flex items-center px-6 py-2.5 text-sm text-gray-300 hover:bg-white/5 hover:text-white transition-colors gap-3"
              href="https://lucafaggianelli.github.io/plombery/"
              target="_blank"
              rel="noopener noreferrer"
            >
              <BookOpenIcon className="w-4 h-4 text-gray-500" />
              <span className="flex-grow">Plombery docs</span>
              <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5 text-gray-600" />
            </a>

            <a
              className="flex items-center px-6 py-2.5 text-sm text-gray-300 hover:bg-white/5 hover:text-white transition-colors gap-3"
              href={getApiUrl().replace(/\/api$/, '/docs')}
              target="_blank"
              rel="noopener noreferrer"
            >
              <CodeBracketSquareIcon className="w-4 h-4 text-gray-500" />
              <span className="flex-grow">REST API docs</span>
              <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5 text-gray-600" />
            </a>

            <a
              className="flex items-center px-6 py-2.5 text-sm text-gray-300 hover:bg-white/5 hover:text-white transition-colors gap-3"
              href="https://github.com/lucafaggianelli/plombery"
              target="_blank"
              rel="noopener noreferrer"
            >
              <ArchiveBoxIcon className="w-4 h-4 text-gray-500" />
              <span className="flex-grow">GitHub</span>
              <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5 text-gray-600" />
            </a>
          </div>

          <div className="h-px bg-white/5 mx-4 my-2" />

          <div className="px-4 py-2">
            <ThemeSwitch />
          </div>

          <div className="px-6 py-2 text-center text-xs text-gray-600">
            Plombery v{version}{' '}
            {isNewerRelease && (
              <span className="text-amber-500 ml-1">
                (v{ghLatestRelease.data?.tag_name} available)
              </span>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}

export default SettingsMenu
