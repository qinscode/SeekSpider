import {
  ArrowTopRightOnSquareIcon,
  PauseIcon,
} from '@heroicons/react/24/outline'
import { useNavigate } from 'react-router'

import { Pipeline } from '@/types'

interface Props {
  pipeline: Pipeline
}

const TriggersList: React.FC<Props> = ({ pipeline }) => {
  const navigate = useNavigate()

  return (
    <div className="glass-panel rounded-2xl overflow-hidden shadow-glass flex flex-col h-full">
      <div className="px-6 py-4 border-b border-white/10 flex justify-between items-center backdrop-blur-xl bg-dark-900/60 z-10 shrink-0">
        <h2 className="text-lg font-bold text-white tracking-tight">Triggers</h2>
        {!pipeline.scheduleEnabled && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-500 text-xs font-medium">
            <PauseIcon className="w-3.5 h-3.5" />
            <span>Scheduled runs paused</span>
          </div>
        )}
      </div>

      <div className="overflow-auto custom-scrollbar">
        <table className="w-full text-left border-collapse">
          <thead className="bg-dark-950/50 backdrop-blur-md sticky top-0 z-10">
            <tr>
              <th className="py-3 px-6 text-xs font-bold text-gray-500 uppercase tracking-widest border-b border-white/5">Name</th>
              <th className="py-3 px-6 text-xs font-bold text-gray-500 uppercase tracking-widest border-b border-white/5">Interval</th>
              <th className="py-3 px-6 text-xs font-bold text-gray-500 uppercase tracking-widest border-b border-white/5">Next Fire Time</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-white/5 font-mono text-sm">
            {pipeline.triggers.map((trigger) => (
              <tr
                key={trigger.id}
                className="group hover:bg-white/5 transition-colors cursor-pointer"
                onClick={() =>
                  navigate(`/pipelines/${pipeline.id}/triggers/${trigger.id}`)
                }
              >
                <td className="py-3 px-6 text-gray-300 group-hover:text-white transition-colors">
                  {trigger.name}
                </td>
                <td className="py-3 px-6 text-gray-400">
                  {trigger.schedule}
                </td>
                <td className="py-3 px-6">
                  {!pipeline.scheduleEnabled ? (
                    <div className="flex items-center gap-1.5 text-amber-500/80 text-xs">
                      <PauseIcon className="w-3.5 h-3.5" />
                      <span>Schedule off</span>
                    </div>
                  ) : trigger.paused ? (
                    <div className="flex items-center gap-1.5 text-amber-500/80 text-xs">
                      <PauseIcon className="w-3.5 h-3.5" />
                      <span>Paused</span>
                    </div>
                  ) : (
                    <span className="text-neon-400">
                      {trigger.next_fire_time?.toLocaleString() || '—'}
                    </span>
                  )}
                </td>
              </tr>
            ))}

            {pipeline.triggers.length === 0 && (
              <tr>
                <td colSpan={3} className="py-12 text-center">
                  <p className="text-gray-500 italic mb-3">
                    This pipeline has no triggers, can be run only manually.
                  </p>

                  <a
                    href="https://lucafaggianelli.github.io/plombery/triggers/"
                    target="_blank"
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 hover:text-indigo-300 transition-all text-xs font-medium no-underline border border-indigo-500/20 hover:border-indigo-500/40"
                    rel="noopener noreferrer"
                  >
                    How to create triggers
                    <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5" />
                  </a>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default TriggersList
