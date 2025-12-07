import { ArrowRightStartOnRectangleIcon } from '@heroicons/react/24/outline'


import { useAuthState } from '@/contexts/AuthContext'

const UserInfo: React.FC = () => {
  const { logout, user } = useAuthState()

  if (!user) {
    return <div>Not authenticated</div>
  }

  return (
    <div className="flex items-center justify-between gap-4 px-6 mb-4">
      <div className="min-w-0">
        <div className="font-medium text-gray-200 truncate">{user.name}</div>
        <div className="text-xs text-gray-500 truncate">
          {user.email}
        </div>
      </div>

      <button
        onClick={async () => await logout()}
        className="p-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
        title="Logout"
      >
        <ArrowRightStartOnRectangleIcon className="w-4 h-4" />
      </button>
    </div>
  )
}

export default UserInfo
