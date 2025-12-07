import { WrenchScrewdriverIcon } from '@heroicons/react/24/outline'

import { useState } from 'react'

import { Trigger } from '@/types'
import Dialog from './Dialog'

interface Props {
  trigger: Trigger
}

const TriggerParamsDialog: React.FC<Props> = ({ trigger }) => {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 hover:bg-cyan-500/20 hover:border-cyan-500/30 hover:shadow-[0_0_10px_rgba(34,211,238,0.15)] transition-all"
      >
        <WrenchScrewdriverIcon className="w-3.5 h-3.5" />
        Show params
      </button>

      <Dialog
        isOpen={open}
        title="Trigger params"
        subtitle={trigger.name}
        footer={
          <button
            onClick={() => setOpen(false)}
            className="px-4 py-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 hover:bg-cyan-500/20 hover:border-cyan-500/30 hover:shadow-[0_0_15px_rgba(34,211,238,0.25)] font-medium transition-all"
          >
            Close
          </button>
        }
        onClose={() => setOpen(false)}
      >
        <pre className="p-4 bg-[#0a0e17] rounded-lg text-sm font-mono text-cyan-400 overflow-auto border border-white/5 shadow-inner">
          {JSON.stringify(trigger.params, null, 2)}
        </pre>
      </Dialog>
    </>
  )
}

export default TriggerParamsDialog
