

interface Props {
  message?: string
}

const LoadingPage: React.FC<Props> = ({ message = 'Loading...' }) => {
  return (
    <div className="bg-[#0a0e17] min-h-screen flex items-center justify-center">
      <div className="flex flex-col items-center justify-center gap-6">
        <div className="relative w-16 h-16">
          <div className="absolute top-0 left-0 w-full h-full">
            <div className="w-16 h-16 border-4 border-white/10 rounded-full" />
          </div>
          <div className="absolute top-0 left-0 w-full h-full animate-spin">
            <div className="w-16 h-16 border-4 border-transparent border-t-neon-500 rounded-full shadow-[0_0_15px_rgba(6,182,212,0.5)]" />
          </div>
        </div>
        <div className="text-gray-400 font-medium tracking-wide animate-pulse">
          {message}
        </div>
      </div>
    </div>
  )
}

export default LoadingPage
