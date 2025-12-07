import { useState } from 'react'

import { TableCellsIcon } from '@heroicons/react/24/outline'

import { Pipeline, PipelineRun } from '@/types'
import { STATUS_COLORS, STATUS_ICONS, getTasksColors } from '@/utils'
import DataViewerDialog from './DataViewerDialog'

interface Props {
  pipeline: Pipeline
  run: PipelineRun
}

const RunsTasksList: React.FC<Props> = ({ pipeline, run }) => {
  const [viewDataDialog, setViewDataDialog] = useState<string | undefined>()

  const tasksColors = getTasksColors(pipeline.tasks)

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-glass flex flex-col h-full col-span-2">
      <DataViewerDialog
        runId={run.id}
        taskId={viewDataDialog || ''}
        open={!!viewDataDialog}
        onClose={() => setViewDataDialog(undefined)}
      />

      <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">Tasks</h2>

      <div className="space-y-2">
        {pipeline.tasks.map((task, i) => {
          const taskRun = run.tasks_run?.[i]
          const status = taskRun?.status || 'pending'
          const statusColor = STATUS_COLORS[status]
          const StatusIcon = STATUS_ICONS[status]

          return (
            <div
              key={task.id}
              className="flex items-center gap-4 p-3 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 transition-colors group"
            >
              <div className={`p-2 rounded-lg bg-${statusColor}-500/10 text-${statusColor}-500`}>
                <StatusIcon className="w-5 h-5" />
              </div>

              <div className="flex-grow min-w-0">
                <div className="flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${tasksColors[task.id]}`} />
                  <span className="font-medium text-gray-200 truncate">{task.name}</span>
                </div>
                {task.description && (
                  <div className="text-sm text-gray-500 truncate mt-0.5">
                    {task.description}
                  </div>
                )}
              </div>

              {taskRun?.has_output && (
                <button
                  onClick={() => setViewDataDialog(task.id)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/20 hover:border-indigo-500/30 transition-all opacity-0 group-hover:opacity-100"
                >
                  <TableCellsIcon className="w-3.5 h-3.5" />
                  Data
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default RunsTasksList
