

import { PipelineRunStatus } from '@/types'
import { STATUS_COLORS, STATUS_ICONS } from '@/utils'

interface Props {
  status: PipelineRunStatus
}

const StatusBadge: React.FC<Props> = ({ status }) => {
  const Icon = STATUS_ICONS[status]
  const color = STATUS_COLORS[status]
  
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border
        ${
          color === 'emerald'
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
            : color === 'red'
            ? 'bg-red-500/10 text-red-400 border-red-500/20'
            : color === 'amber'
            ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
            : color === 'sky'
            ? 'bg-sky-500/10 text-sky-400 border-sky-500/20'
            : 'bg-slate-500/10 text-slate-400 border-slate-500/20'
        }
      `}
    >
      <Icon className="w-3.5 h-3.5" />
      <span className="capitalize">{status}</span>
    </span>
  )
}

export default StatusBadge
