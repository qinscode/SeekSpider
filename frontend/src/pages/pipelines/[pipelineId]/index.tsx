import { Switch } from '@headlessui/react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router'
import React from 'react'
import { ArrowTopRightOnSquareIcon } from '@heroicons/react/24/outline'

import Navbar from '@/components/Navbar'
import Breadcrumbs from '@/components/Breadcrumbs'
import LoadingPage from '@/components/LoadingPage'
import RunsDurationChart from '@/components/RunsDurationChart'
import RunsList from '@/components/RunsList'
import RunsStatusChart from '@/components/RunsStatusChart'
import {
  getPipeline,
  listRuns,
  updatePipelineScheduleState,
} from '@/repository'
import ManualRunDialog from '@/components/ManualRunDialog'
import TriggersList from '@/components/TriggersList'
import PipelineHttpRun from '@/components/help/PipelineHttpRun'
import { Pipeline, PipelineScheduleState } from '@/types'

const PipelineView: React.FC = () => {
  const urlParams = useParams()
  const pipelineId = urlParams.pipelineId as string

  const queryClient = useQueryClient()
  const pipelineQuery = useQuery(getPipeline(pipelineId))
  const runsQuery = useQuery(listRuns(pipelineId))
  const scheduleMutation = useMutation({
    ...updatePipelineScheduleState(pipelineId),
    onSuccess: (data: PipelineScheduleState) => {
      queryClient.setQueryData(['pipeline', pipelineId], (prev: Pipeline) => {
        if (!prev) return prev

        return new Pipeline(
          prev.id,
          prev.name,
          prev.description,
          prev.tasks,
          prev.triggers,
          data.schedule_enabled
        )
      })

      queryClient.setQueryData(['pipelines'], (prev: Pipeline[] | undefined) => {
        if (!prev) return prev

        return prev.map((p) =>
          p.id === pipelineId
            ? new Pipeline(
                p.id,
                p.name,
                p.description,
                p.tasks,
                p.triggers,
                data.schedule_enabled
              )
            : p
        )
      })
    },
  })

  if (pipelineQuery.isPending) return <LoadingPage message="Loading pipeline details..." />

  if (pipelineQuery.isError) return <LoadingPage message="Error loading pipeline" />

  const pipeline = pipelineQuery.data
  const scheduleToggleDisabled = scheduleMutation.isPending || pipelineQuery.isFetching

  return (
    <div className="text-gray-300 antialiased h-screen flex flex-col overflow-hidden font-sans bg-[#0a0e17]">
      <Navbar>
        <div className="flex flex-col gap-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex flex-col min-w-0">
              <h1 className="text-2xl font-bold text-white tracking-tight truncate flex items-center gap-3">
                Pipeline {pipeline.name}
              </h1>
              {pipeline.description && (
                <p className="text-gray-500 truncate mt-1">
                  {pipeline.description}
                </p>
              )}
            </div>

            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-3 bg-dark-900/50 rounded-full px-4 py-2 border border-white/5">
                <Switch
                  checked={pipeline.scheduleEnabled}
                  disabled={scheduleToggleDisabled}
                  onChange={(checked) => scheduleMutation.mutate(checked)}
                  className={`${
                    pipeline.scheduleEnabled
                      ? 'bg-neon-600'
                      : 'bg-gray-700'
                  } relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                    scheduleToggleDisabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'
                  }`}
                >
                  <span className="sr-only">Toggle scheduled runs</span>
                  <span
                    className={`${
                      pipeline.scheduleEnabled ? 'translate-x-6' : 'translate-x-1'
                    } inline-block h-4 w-4 transform rounded-full bg-white transition`}
                  />
                </Switch>
                <div className="flex flex-col">
                  <span className={`text-xs font-bold uppercase tracking-wider ${pipeline.scheduleEnabled ? 'text-neon-400' : 'text-gray-500'}`}>
                    {pipeline.scheduleEnabled ? 'Schedule On' : 'Schedule Off'}
                  </span>
                </div>
              </div>

              <ManualRunDialog 
                pipeline={pipeline} 
                trigger={
                  <button className="flex items-center gap-2 bg-neon-600 hover:bg-neon-500 text-white px-4 py-2 rounded-lg font-medium transition-all shadow-[0_0_15px_rgba(6,182,212,0.3)] hover:shadow-[0_0_20px_rgba(6,182,212,0.5)]">
                    <span className="w-0 h-0 border-t-[5px] border-t-transparent border-l-[8px] border-l-white border-b-[5px] border-b-transparent ml-0.5"></span>
                    Run Pipeline
                  </button>
                }
              />
            </div>
          </div>

          <Breadcrumbs pipeline={pipeline} />
        </div>
      </Navbar>

      <main className="flex-1 overflow-y-auto custom-scrollbar p-6 max-w-[1800px] mx-auto w-full relative z-10 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Tasks Card */}
          <div className="glass-panel rounded-2xl p-6 flex flex-col h-full shadow-glass">
            <h2 className="text-lg font-bold text-white tracking-tight mb-4">Tasks</h2>

            <ul className="space-y-3 flex-1">
              {pipeline.tasks.map((task) => (
                <li key={task.id} className="p-3 rounded-lg bg-white/5 border border-white/5">
                  <div className="font-bold text-gray-200">{task.name}</div>
                  {task.description && (
                    <div className="text-sm text-gray-500 truncate mt-1" title={task.description}>
                      {task.description}
                    </div>
                  )}
                </li>
              ))}

              {pipeline.tasks.length === 0 && (
                <li className="text-center py-8">
                  <p className="text-gray-500 italic mb-3">
                    This pipeline has no tasks so it can't be run.
                  </p>

                  <a
                    href="https://lucafaggianelli.github.io/plombery/tasks/"
                    target="_blank"
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 hover:text-indigo-300 transition-all text-xs font-medium no-underline border border-indigo-500/20 hover:border-indigo-500/40"
                    rel="noopener noreferrer"
                  >
                    How to create tasks
                    <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5" />
                  </a>
                </li>
              )}
            </ul>

            <div className="mt-6 pt-6 border-t border-white/10 flex justify-between items-center gap-4">
              <span className="text-sm text-gray-400 font-medium">Run URL</span>
              <PipelineHttpRun pipelineId={pipelineId} />
            </div>
          </div>

          <RunsStatusChart subject="Pipeline" query={runsQuery} />
          <RunsDurationChart query={runsQuery} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[600px]">
          <TriggersList pipeline={pipeline} />
          <RunsList query={runsQuery} pipelineId={pipelineId} />
        </div>
      </main>
    </div>
  )
}

export default PipelineView
