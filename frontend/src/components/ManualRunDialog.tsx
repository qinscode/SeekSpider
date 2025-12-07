import { PlayIcon } from '@heroicons/react/24/outline'
import { useMutation, useQuery } from '@tanstack/react-query'

import { useState } from 'react'
import { useNavigate } from 'react-router'

import { getPipelineInputSchema, runPipeline } from '../repository'
import { Pipeline } from '../types'
import Dialog from './Dialog'
import JsonSchemaForm from './JsonSchemaForm'
import FlowMeterParamsForm from './FlowMeterParamsForm'


interface Props {
  pipeline: Pipeline
  trigger?: React.ReactNode
}

const ManualRunDialog: React.FC<Props> = ({ pipeline, trigger }) => {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()


  const query = useQuery({
    ...getPipelineInputSchema(pipeline.id),
    enabled: open,
  })

  const runPipelineMutation = useMutation(runPipeline(pipeline.id))

  const formErrors =
    runPipelineMutation.isError && runPipelineMutation.error.status === 422
      ? Object.fromEntries(
          runPipelineMutation.error.data.data.detail.map((detail: any) => [
            detail.loc.join('.'),
            detail.msg,
          ])
        )
      : undefined

  const genericError = runPipelineMutation.error?.message

  return (
    <>
      {trigger ? (
        <div onClick={() => setOpen(true)} className="cursor-pointer">
          {trigger}
        </div>
      ) : (
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 hover:bg-cyan-500/20 hover:border-cyan-500/30 hover:shadow-[0_0_15px_rgba(34,211,238,0.15)] transition-all"
        >
          <PlayIcon className="w-3.5 h-3.5" />
          Run
        </button>
      )}

          <Dialog
        isOpen={open}
        title={`Run ${pipeline.name} manually`}
        onClose={() => setOpen(false)}
        disableOutsideClick={
          pipeline.id === 'flow_meter_scraper' ||
          pipeline.id === 'dust_level_scraper'
        }
        footer={
          <>
            <button
              type="button"
              onClick={() => setOpen(false)}
              disabled={runPipelineMutation.isPending}
              className="px-4 py-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
            >
              Close
            </button>

            <button
              onClick={(e) => {
                // Trigger form submission
                const form = document.getElementById('manual-run-form') as HTMLFormElement
                if (form) form.requestSubmit()
              }}
              disabled={runPipelineMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 hover:bg-cyan-500/20 hover:border-cyan-500/30 hover:shadow-[0_0_15px_rgba(34,211,238,0.25)] font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
            >
              <PlayIcon className="w-5 h-5" />
              Run
            </button>
          </>
        }
      >
        <form
          id="manual-run-form"
          onSubmit={async (event) => {
            event.preventDefault()

            const params = Object.fromEntries(
              new FormData(event.target as HTMLFormElement).entries()
            )

            try {
              const data = await runPipelineMutation.mutateAsync(params)
              navigate(
                `/pipelines/${data.pipeline_id}/triggers/${data.trigger_id}/runs/${data.id}`
              )
              setOpen(false)
            } catch (error) {
              console.error(error)
            }
          }}
        >

          {query.isPending || query.isFetching ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin shadow-[0_0_15px_rgba(34,211,238,0.25)]" />
            </div>
          ) : query.isError ? (
            <div className="text-red-400 p-4 text-center font-mono text-sm">Error loading parameters</div>
          ) : (
            <div className="space-y-4 max-h-[60vh] overflow-y-auto custom-scrollbar pr-2">
              {pipeline.id === 'flow_meter_scraper' ? (
                <FlowMeterParamsForm errors={formErrors} />
              ) : (
                <JsonSchemaForm schema={query.data} errors={formErrors} />
              )}

              {genericError && (
                <div className="text-sm text-red-400 mt-2 font-mono">
                  {genericError}
                </div>
              )}
            </div>
          )}
        </form>
      </Dialog>
    </>
  )
}

export default ManualRunDialog
