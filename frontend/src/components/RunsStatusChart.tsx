import { UseQueryResult } from '@tanstack/react-query'
import { HTTPError } from 'ky'

import { PipelineRun } from '../types'
import ErrorAlert from './queries/Error'
import { MetricLoader, TextLoader, TrackerLoader } from './queries/Loaders'

interface Props {
  query: UseQueryResult<PipelineRun[], HTTPError>
  subject: 'Trigger' | 'Pipeline'
}

const Loader = ({ subject }: { subject: string }) => (
  <div className="glass-panel rounded-2xl p-6 shadow-glass flex flex-col h-full">
    <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-1">Successful runs</h2>

    <MetricLoader />

    <div className="mt-auto">
      <h3 className="text-xs font-medium text-gray-500 mb-3 uppercase tracking-wider">{subject} health</h3>
      <TrackerLoader />
      <div className="flex justify-between mt-2">
        <TextLoader className="w-20" />
        <TextLoader className="w-20" />
      </div>
    </div>
  </div>
)

const RunsStatusChart: React.FC<Props> = ({ query, subject }) => {
  if (query.isPending || query.isFetching) {
    return <Loader subject={subject} />
  }

  if (query.isError) {
    return (
      <div className="glass-panel rounded-2xl p-6 shadow-glass h-full">
        <ErrorAlert query={query} />
      </div>
    )
  }

  const runs = [...query.data].reverse()
  const successfulRuns = runs.filter((run) => run.status === 'completed')

  const successPercentage = (successfulRuns.length / runs.length) * 100 || 0

  const fromDate = runs[0]?.start_time
  const toDate = runs[runs.length - 1]?.start_time

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-glass flex flex-col h-full">
      <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-1">Successful runs</h2>

      <div className="flex items-baseline gap-2 mb-6">
        <span className="text-4xl font-bold text-white tracking-tight">
          {successPercentage.toFixed(1)}
        </span>
        <span className="text-lg font-medium text-neon-400">%</span>
      </div>

      {runs.length ? (
        <div className="flex-1 flex flex-col justify-end">
          <h3 className="text-xs font-medium text-gray-500 mb-3 uppercase tracking-wider">{subject} health</h3>
          
          <div className="flex gap-[2px] h-8 w-full">
            {runs.map((run) => (
              <div
                key={run.id}
                className={`flex-1 rounded-sm transition-all hover:opacity-80 relative group ${
                  run.status === 'completed'
                    ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]'
                    : run.status === 'failed'
                    ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]'
                    : 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.4)]'
                }`}
              >
                <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-dark-900 border border-white/10 text-xs px-2 py-1 rounded shadow-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                  #{run.id} <span className="capitalize">{run.status}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="flex justify-between mt-3 text-xs text-gray-500 font-mono">
            <span>{fromDate && fromDate.toDateString()}</span>
            <span>{toDate && toDate.toDateString()}</span>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-gray-500 italic text-sm">
          This {subject.toLowerCase()} has no runs yet
        </div>
      )}
    </div>
  )
}

export default RunsStatusChart
