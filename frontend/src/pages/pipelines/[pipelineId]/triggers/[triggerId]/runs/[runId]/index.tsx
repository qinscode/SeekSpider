import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { addMilliseconds, isSameDay } from 'date-fns'
import { useParams } from 'react-router'
import { useEffect, useState } from 'react'
import ky from 'ky'

import Breadcrumbs from '@/components/Breadcrumbs'
import Navbar from '@/components/Navbar'
import LoadingPage from '@/components/LoadingPage'
import LogViewer from '@/components/LogViewer'
import StatusBadge from '@/components/StatusBadge'
import RunsTasksList from '@/components/Tasks'
import Timer from '@/components/Timer'
import { MANUAL_TRIGGER } from '@/constants'
import { getPipeline, getRun } from '@/repository'
import { socket } from '@/socket'
import { Trigger } from '@/types'
import { TASKS_COLORS, formatDate, formatDateTime, formatTime } from '@/utils'

const RunViewPage = () => {
  const queryClient = useQueryClient()
  const urlParams = useParams()
  const pipelineId = urlParams.pipelineId as string
  const triggerId = urlParams.triggerId as string
  const runId = parseInt(urlParams.runId as string)
  const [cancelling, setCancelling] = useState(false)

  // Mutation for cancelling run
  const cancelRunMutation = useMutation({
    mutationFn: async () => {
      setCancelling(true)
      const response = await ky.post(`/api/runs/${runId}/cancel`).json<{ message: string }>()
      return response
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: getRun(pipelineId, triggerId, runId).queryKey,
      })
    },
    onSettled: () => {
      setCancelling(false)
    },
  })

  useEffect(() => {
    const onRunUpdate = () => {
      queryClient.invalidateQueries({
        queryKey: getRun(pipelineId, triggerId, runId).queryKey,
      })
    }
    socket.on('run-update', onRunUpdate)

    return () => {
      socket.off('run-update', onRunUpdate)
    }
  }, [pipelineId])

  const pipelineQuery = useQuery(getPipeline(pipelineId))
  const runQuery = useQuery({
    ...getRun(pipelineId, triggerId, runId),
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 3000),
  })

  if (pipelineQuery.isPending || runQuery.isPending) {
    return <LoadingPage message="Loading run details..." />
  }

  if (pipelineQuery.isError) {
    return <LoadingPage message="Error loading pipeline" />
  }

  if (runQuery.isError) {
    return <LoadingPage message="Error loading run" />
  }

  const pipeline = pipelineQuery.data

  const isManualTrigger = triggerId === MANUAL_TRIGGER.id
  const trigger: Trigger | undefined = !isManualTrigger
    ? pipeline.triggers.find((trigger) => trigger.id === triggerId)
    : MANUAL_TRIGGER

  const run = runQuery.data

  if (!run) {
    return <div>Run not found</div>
  }

  if (!trigger) {
    return <div>Trigger not found</div>
  }

  const totalTasksDuration = (run.tasks_run || []).reduce(
    (tot, cur) => tot + cur.duration,
    0
  )
  const tasksRunDurations = (run.tasks_run || []).map((tr) =>
    totalTasksDuration ? (tr.duration / totalTasksDuration) * 100 : 0
  )

  const runEndTime = addMilliseconds(run.start_time, run.duration)

  // @ts-ignore
    return (
    <div className="dark text-gray-300 antialiased h-screen flex flex-col overflow-hidden font-sans bg-[#0a0e17]">
      <Navbar>
        <div className="flex flex-col gap-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex flex-col min-w-0">
              <h1 className="text-2xl font-bold text-white tracking-tight truncate flex items-center gap-3">
                Run #{runId}
                {run.status === 'running' && (
                  <button
                    onClick={() => cancelRunMutation.mutate()}
                    disabled={cancelling}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-800 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    {cancelling ? 'Cancelling...' : 'Cancel Run'}
                  </button>
                )}
              </h1>
            </div>
          </div>

          <Breadcrumbs pipeline={pipeline} trigger={trigger} run={run} />
        </div>
      </Navbar>

      <main className="flex-1 overflow-y-auto custom-scrollbar p-6 max-w-[1800px] mx-auto w-full relative z-10 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <RunsTasksList pipeline={pipeline} run={run} />

          <div className="glass-panel rounded-2xl p-6 shadow-glass flex flex-col h-full">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Duration</h2>
              <StatusBadge status={run.status} />
            </div>

            <div className="flex items-baseline gap-2 mb-6">
              <span className="text-4xl font-bold text-white tracking-tight">
                {run.status !== 'running' ? (
                  (run.duration / 1000).toFixed(2)
                ) : (
                  <Timer startTime={run.start_time} />
                )}
              </span>
              <span className="text-lg font-medium text-neon-400">s</span>
            </div>

            <div className="w-full h-3 rounded-full bg-dark-900 overflow-hidden flex mb-4">
              {tasksRunDurations.map((percentage, i) => (
                <div
                  key={i}
                  className={`h-full ${TASKS_COLORS[i % TASKS_COLORS.length]}`}
                  style={{ width: `${percentage}%` }}
                />
              ))}
            </div>

            <div className="flex items-start justify-between mt-auto pt-4 border-t border-white/5">
              <div>
                <div className="text-white font-bold" title={formatDateTime(run.start_time, true)}>
                  {formatTime(run.start_time)}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">{formatDate(run.start_time)}</div>
              </div>

              <div className="text-right">
                <div className="text-white font-bold" title={formatDateTime(runEndTime, true)}>
                  {formatTime(runEndTime)}
                </div>
                {!isSameDay(run.start_time, runEndTime) && (
                  <div className="text-xs text-gray-500 mt-0.5">{formatDate(runEndTime)}</div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="glass-panel rounded-2xl overflow-hidden shadow-glass">
          <LogViewer pipeline={pipeline} run={run} />
        </div>
      </main>
    </div>
  )
}

export default RunViewPage
