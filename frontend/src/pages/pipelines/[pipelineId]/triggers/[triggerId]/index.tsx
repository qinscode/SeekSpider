import { useQuery, useMutation } from '@tanstack/react-query'
import { PlayIcon } from '@heroicons/react/24/outline'
import { useNavigate, useParams } from 'react-router'
import React from 'react'

import TriggerParamsDialog from '@/components/TriggerParamsDialog'
import Navbar from '@/components/Navbar'
import Breadcrumbs from '@/components/Breadcrumbs'
import LoadingPage from '@/components/LoadingPage'
import ManualRunDialog from '@/components/ManualRunDialog'
import RunsDurationChart from '@/components/RunsDurationChart'
import RunsList from '@/components/RunsList'
import RunsStatusChart from '@/components/RunsStatusChart'
import { MANUAL_TRIGGER } from '@/constants'
import { getPipeline, listRuns, runPipeline } from '@/repository'
import { Trigger } from '@/types'
import PipelineHttpRun from '@/components/help/PipelineHttpRun'

const TriggerView: React.FC = () => {
  const navigate = useNavigate()
  const urlParams = useParams()
  const pipelineId = urlParams.pipelineId as string
  const triggerId = urlParams.triggerId as string

  const pipelineQuery = useQuery(getPipeline(pipelineId))

  const runsQuery = useQuery({
    ...listRuns(pipelineId, triggerId),
    enabled: !!triggerId,
  })

  const runPipelineMutation = useMutation({
    ...runPipeline(pipelineId, triggerId),
    onSuccess(data) {
      navigate(
        `/pipelines/${data.pipeline_id}/triggers/${data.trigger_id}/runs/${data.id}`
      )
    },
  })

  if (pipelineQuery.isPending) return <LoadingPage message="Loading trigger details..." />

  if (pipelineQuery.isError) return <LoadingPage message="Error loading trigger" />

  const pipeline = pipelineQuery.data

  const isManualTrigger = triggerId === MANUAL_TRIGGER.id
  const trigger: Trigger | undefined = !isManualTrigger
    ? pipeline.triggers.find((trigger) => trigger.id === triggerId)
    : MANUAL_TRIGGER

  if (!trigger) {
    return <div>Trigger not found</div>
  }

  const runTriggerButton = isManualTrigger ? (
    <ManualRunDialog pipeline={pipeline} />
  ) : (
    <button
      onClick={() => {
        runPipelineMutation.mutateAsync()
      }}
      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white font-medium transition-all shadow-[0_0_15px_rgba(99,102,241,0.5)] hover:shadow-[0_0_20px_rgba(99,102,241,0.7)]"
    >
      <PlayIcon className="w-5 h-5" />
      Run
    </button>
  )

  return (
    <div className="dark text-gray-300 antialiased h-screen flex flex-col overflow-hidden font-sans bg-[#0a0e17]">
      <Navbar>
        <div className="flex flex-col gap-4">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="flex flex-col min-w-0">
              <h1 className="text-2xl font-bold text-white tracking-tight truncate flex items-center gap-3">
                Trigger {trigger.name}
              </h1>
              {trigger.description && (
                <p className="text-sm text-gray-400 mt-1 truncate max-w-full">
                  {trigger.description}
                </p>
              )}
            </div>

            {runTriggerButton}
          </div>

          <Breadcrumbs
            pipeline={pipeline}
            trigger={trigger}
          />
        </div>
      </Navbar>

      <main className="flex-1 overflow-y-auto custom-scrollbar p-6 max-w-[1800px] mx-auto w-full relative z-10 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="glass-panel rounded-2xl p-6 shadow-glass flex flex-col h-full">
            <h2 className="text-lg font-semibold text-white mb-2">{trigger.name}</h2>
            <p className="text-sm text-gray-400 mb-6">{trigger.description}</p>

            <div className="flex-grow" />

            <div className="space-y-4">
              <div className="flex items-center justify-between py-2 border-b border-white/5">
                <span className="text-sm text-gray-400">Schedule</span>
                <span className="text-sm font-mono text-neon-400">{trigger.schedule}</span>
              </div>

              <div className="flex items-center justify-between py-2 border-b border-white/5">
                <span className="text-sm text-gray-400">Params</span>
                {trigger.params ? (
                  <TriggerParamsDialog trigger={trigger} />
                ) : (
                  <span className="text-sm text-gray-500 italic">No params</span>
                )}
              </div>

              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-gray-400">Run URL</span>
                <PipelineHttpRun pipelineId={pipelineId} triggerId={triggerId} />
              </div>
            </div>
          </div>

          <RunsStatusChart subject="Trigger" query={runsQuery} />

          <RunsDurationChart query={runsQuery} />
        </div>

        <div className="mt-6">
          <RunsList
            query={runsQuery}
            pipelineId={pipelineId}
            triggerId={triggerId}
          />
        </div>
      </main>
    </div>
  )
}

export default TriggerView
