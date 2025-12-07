import { UseQueryResult, useQueryClient } from '@tanstack/react-query'
import { formatDistanceToNow, differenceInDays } from 'date-fns'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { HTTPError } from 'ky'

import { socket } from '@/socket'
import { PipelineRun } from '@/types'
import { formatDateTime } from '@/utils'
import Timer from './Timer'
import ErrorAlert from './queries/Error'

import { TableLoader } from './queries/Loaders'

const toValidDate = (value: any): Date => {
  const d = new Date(value)
  return isNaN(d.getTime()) ? new Date() : d
}

interface Props {
  pipelineId?: string
  query: UseQueryResult<PipelineRun[], HTTPError>
  triggerId?: string
}

const RunsList: React.FC<Props> = ({ pipelineId, query, triggerId }) => {
  const [runs, setRuns] = useState<PipelineRun[]>(query.data || [])
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const onWsMessage = useCallback(
    (data: any) => {
      const run = {
        ...data.run,
        start_time: toValidDate(data.run.start_time),
        trigger_id: data.trigger,
        pipeline_id: data.pipeline,
      }

      setRuns((prevRuns) => {
        if (run.status === 'running') {
          return [run, ...prevRuns]
        }

        const nextRuns = [...prevRuns]
        const idx = nextRuns.findIndex((r) => r.id === run.id)

        if (idx >= 0) {
          nextRuns[idx] = run
        } else {
          nextRuns.unshift(run)
        }

        return nextRuns
      })

      if (run.status !== 'running') {
        queryClient.invalidateQueries({
          queryKey: ['runs', pipelineId, triggerId],
        })
      }
    },
    [pipelineId, queryClient, triggerId]
  )

  useEffect(() => {
    socket.on('run-update', onWsMessage)

    return () => {
      socket.off('run-update', onWsMessage)
    }
  }, [onWsMessage])

  useEffect(() => {
    if (query.data) {
      setRuns(query.data)
    }
  }, [query.data])

  const numberOfColumns = 4 + Number(!!pipelineId) + Number(!!triggerId)


  return (
    <div className="flex-1 flex flex-col glass-panel rounded-2xl overflow-hidden shadow-glass h-full">
      <div className="px-6 py-4 border-b border-white/10 flex justify-between items-center backdrop-blur-xl bg-dark-900/60 z-10 shrink-0">
        <h2 className="text-lg font-bold text-white tracking-tight">
          Run History
        </h2>
        <div className="text-xs font-mono text-gray-500">Live updating</div>
      </div>

      <div className="flex-1 overflow-auto custom-scrollbar">
        <table className="w-full text-left border-collapse">
          <thead className="bg-dark-950/50 backdrop-blur-md sticky top-0 z-10">
            <tr>
              <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-widest w-20">
                #
              </th>
              <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-widest w-36">
                Status
              </th>
              {!pipelineId && (
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-widest">
                  Pipeline
                </th>
              )}
              {!triggerId && (
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-widest w-48">
                  Trigger
                </th>
              )}
              <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-widest w-48">
                Started at
              </th>
              <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-widest w-32 text-right">
                Duration
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 font-mono text-sm">
            {runs.map((run) => (
              <tr
                key={run.id}
                className={`hover:bg-white/5 transition-colors group cursor-pointer ${
                  run.status === 'running' ? 'bg-neon-900/10' : ''
                }`}
                onClick={() =>
                  navigate(
                    `/pipelines/${run.pipeline_id}/triggers/${run.trigger_id}/runs/${run.id}`
                  )
                }
              >
                <td className="px-6 py-4 text-gray-500">{run.id}</td>
                <td className="px-6 py-4">
                  {run.status === 'completed' && (
                    <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-green-950/40 text-green-400 border border-green-500/20 shadow-[0_0_6px_rgba(34,197,94,0.15)]">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-400 shadow-[0_0_6px_#4ade80]"></span>{' '}
                      Completed
                    </span>
                  )}
                  {run.status === 'running' && (
                    <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-neon-950/40 text-neon-400 border border-neon-500/20 shadow-[0_0_6px_rgba(6,182,212,0.15)]">
                      <svg
                        className="animate-spin h-3 w-3 text-neon-400"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Running
                    </span>
                  )}
                  {run.status === 'failed' && (
                    <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-red-950/40 text-red-400 border border-red-500/20 shadow-[0_0_6px_rgba(248,113,113,0.15)]">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="12"
                        height="12"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>{' '}
                      Failed
                    </span>
                  )}
                  {/* Fallback for other statuses */}
                  {!['completed', 'running', 'failed'].includes(run.status) && (
                     <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-gray-800 text-gray-400 border border-gray-700">
                       {run.status}
                     </span>
                  )}
                </td>
                {!pipelineId && (
                  <td className="px-6 py-4 font-medium text-gray-300 group-hover:text-neon-400 transition-colors">
                    <Link
                      to={`/pipelines/${run.pipeline_id}`}
                      onClick={(event) => event.stopPropagation()}
                    >
                      {run.pipeline_id}
                    </Link>
                  </td>
                )}
                {!triggerId && (
                  <td className="px-6 py-4 text-gray-500">
                    <Link
                      to={`/pipelines/${run.pipeline_id}/triggers/${run.trigger_id}`}
                      onClick={(event) => event.stopPropagation()}
                    >
                      {run.trigger_id}
                    </Link>
                  </td>
                )}
                <td
                  className="px-6 py-4 text-gray-400"
                  title={formatDateTime(run.start_time, true)}
                >
                  {differenceInDays(new Date(), run.start_time) <= 1
                    ? formatDistanceToNow(run.start_time, {
                        addSuffix: true,
                        includeSeconds: true,
                      })
                    : formatDateTime(run.start_time)}
                </td>
                <td className="px-6 py-4 text-gray-400 text-right">
                  {run.status !== 'running' ? (
                    (run.duration / 1000).toFixed(2)
                  ) : (
                    <Timer startTime={run.start_time} />
                  )}{' '}
                  s
                </td>
              </tr>
            ))}

            {(query.isFetching || query.isPending) && (
               <tr>
                 <td colSpan={numberOfColumns} className="px-6 py-4 text-center text-gray-500">
                   Loading...
                 </td>
               </tr>
            )}

            {query.isError && (
              <tr>
                <td colSpan={numberOfColumns} className="px-6 py-4">
                  <ErrorAlert query={query} />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default RunsList
