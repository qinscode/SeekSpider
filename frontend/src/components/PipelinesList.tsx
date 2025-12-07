import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { formatDistanceToNow } from 'date-fns'
import { Link } from 'react-router'
import React from 'react'

import { listPipelines, updatePipelineScheduleState } from '@/repository'
import ManualRunDialog from './ManualRunDialog'
import { ArrowTopRightOnSquareIcon } from '@heroicons/react/24/outline'
import { Text } from '@tremor/react'


const PipelineCard: React.FC<{ pipeline: any }> = ({ pipeline }) => {
  const queryClient = useQueryClient()
  const nextFireTime = pipeline.getNextFireTime()

  const toggleMutation = useMutation({
    ...updatePipelineScheduleState(pipeline.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] })
    },
  })

  const handleToggle = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    toggleMutation.mutate(!pipeline.scheduleEnabled)
  }

  return (
    <div
      className="group glass-panel rounded-2xl p-5 transition-all duration-300 hover:border-neon-500/50 hover:shadow-neon relative overflow-hidden"
    >
      <div className="absolute -top-10 -right-10 w-32 h-32 bg-neon-500/10 rounded-full blur-3xl group-hover:bg-neon-500/20 transition-all"></div>

      <div className="flex justify-between items-start mb-3 relative">
        <h3 className="text-lg font-bold text-white group-hover:text-neon-400 transition-colors">
          <Link to={`/pipelines/${pipeline.id}`}>{pipeline.name}</Link>
        </h3>
        <ManualRunDialog
          pipeline={pipeline}
          trigger={
            <button className="text-neon-400 bg-neon-500/10 hover:bg-neon-500/20 p-2 rounded-lg transition-all shadow-[0_0_10px_rgba(6,182,212,0.1)] hover:shadow-[0_0_15px_rgba(6,182,212,0.4)]">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M8 5v14l11-7z" />
              </svg>
            </button>
          }
        />
      </div>
      <p className="text-sm text-gray-400 mb-5 leading-relaxed relative z-10 line-clamp-2">
        {pipeline.description || 'No description provided'}
      </p>
      <div className="flex items-center justify-between text-xs font-medium relative z-10">
        {pipeline.hasTrigger() && nextFireTime ? (
          <span className="flex items-center gap-2 text-neon-400 font-mono bg-neon-950/30 px-2 py-1 rounded-md border border-neon-900/50">
            <svg
              className="w-4 h-4 animate-pulse"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            {formatDistanceToNow(nextFireTime, {
              addSuffix: true,
              includeSeconds: true,
            })}
          </span>
        ) : (
          <span className="text-gray-500 font-mono">Manual trigger</span>
        )}

        <button
          onClick={handleToggle}
          disabled={toggleMutation.isPending}
          className={`transition-all ${toggleMutation.isPending ? 'opacity-50 cursor-wait' : 'cursor-pointer hover:scale-105'}`}
        >
          {pipeline.scheduleEnabled ? (
            <span className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-950/30 text-green-400 border border-green-500/30 shadow-[0_0_8px_rgba(34,197,94,0.2)] hover:bg-green-950/50 hover:border-green-500/50 transition-all">
              <div className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500 shadow-[0_0_8px_#22c55e]"></span>
              </div>
              Active
            </span>
          ) : (
            <span className="flex items-center gap-2 px-3 py-1 rounded-full bg-yellow-950/30 text-yellow-500 border border-yellow-600/30 hover:bg-yellow-950/50 hover:border-yellow-600/50 transition-all">
              <span className="relative inline-flex rounded-full h-2 w-2 bg-yellow-500 shadow-[0_0_8px_#eab308]"></span>
              Paused
            </span>
          )}
        </button>
      </div>
    </div>
  )
}


const PipelinesList: React.FC = () => {
  const query = useQuery(listPipelines())

  if (query.isPending) return <div>Loading...</div>

  if (query.isError) return <div>An error has occurred</div>

  const pipelines = query.data

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 pl-1">
        Pipelines
      </h2>

      {pipelines.map((pipeline) => (
        <PipelineCard key={pipeline.id} pipeline={pipeline} />
      ))}

      {pipelines.length === 0 && (
        <div className="glass-panel rounded-2xl p-5 text-center">
          <Text className="italic text-gray-400">
            There are no pipelines, you can't do much.
          </Text>

          <div className="text-center mt-4 text-sm">
            <a
              href="https://lucafaggianelli.github.io/plombery/pipelines/"
              target="_blank"
              className="inline-flex items-center gap-2 text-neon-400 hover:text-neon-300 transition-colors"
              rel="noopener noreferrer"
            >
              How to create pipelines
              <ArrowTopRightOnSquareIcon className="w-4 h-4" />
            </a>
          </div>
        </div>
      )}
    </div>
  )
}

export default PipelinesList
