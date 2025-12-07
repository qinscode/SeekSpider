
import { QuestionMarkCircleIcon } from '@heroicons/react/24/outline'
import { useState } from 'react'
import { PrismLight as SyntaxHighlighter } from 'react-syntax-highlighter'
import {

  atomDark as darkTheme,
} from 'react-syntax-highlighter/dist/esm/styles/prism'
import ts from 'react-syntax-highlighter/dist/esm/languages/prism/typescript'
import py from 'react-syntax-highlighter/dist/esm/languages/prism/python'

import CopyButton from '@/components/CopyButton'
import Dialog from '@/components/Dialog'
import { getPipelineRunUrl } from '@/repository'

interface Props {
  pipelineId: string
  triggerId?: string
}

SyntaxHighlighter.registerLanguage('ts', ts)
SyntaxHighlighter.registerLanguage('py', py)

const PipelineHttpRun: React.FC<Props> = ({ pipelineId, triggerId }) => {
  const [open, setOpen] = useState(false)
  const isDark = document.documentElement.classList.contains('dark')

  const SNIPPETS = [
    {
      language: 'python',
      name: 'Python',
      code: `import httpx

httpx.post('${getPipelineRunUrl(pipelineId)}', json={${
        triggerId ? `\n  "trigger_id": "${triggerId}",` : ''
      }
  "params": {
    "name": "value",
  }
})`,
    },
    {
      language: 'js',
      name: 'JavaScript',
      code: `fetch('${getPipelineRunUrl(pipelineId)}', {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({${triggerId ? `\n    trigger_id: '${triggerId}',` : ''}
    params: {},
  }),
})`,
    },
  ]

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="p-1.5 rounded-md text-gray-400 hover:text-cyan-400 hover:bg-cyan-500/10 transition-colors"
        title="Show HTTP request example"
      >
        <QuestionMarkCircleIcon className="w-5 h-5" />
      </button>

      <Dialog
        isOpen={open}
        title="Run via HTTP request"
        subtitle="You can run pipelines and triggers via HTTP requests"
        onClose={() => setOpen(false)}
      >
        <div className="mt-4">
          <div className="flex border-b border-white/5 mb-4">
            {SNIPPETS.map((snippet) => (
              <button
                key={snippet.name}
                onClick={() => {
                  // Tab logic placeholder
                }}
                className="px-4 py-2 text-sm font-medium text-gray-400 hover:text-cyan-400 border-b-2 border-transparent hover:border-cyan-500/50 transition-colors"
              >
                {snippet.name}
              </button>
            ))}
          </div>
          
          <div className="space-y-6">
            {SNIPPETS.map((snippet) => (
              <div key={snippet.name}>
                <h4 className="text-sm font-medium text-gray-300 mb-2 font-mono tracking-tight">{snippet.name}</h4>
                <div className="relative group">
                  <SyntaxHighlighter
                    language={snippet.language}
                    style={darkTheme}
                    customStyle={{ borderRadius: 8, fontSize: 13, background: '#0a0e17', border: '1px solid rgba(255,255,255,0.05)', fontFamily: 'monospace' }}
                  >
                    {snippet.code}
                  </SyntaxHighlighter>

                  <CopyButton
                    content={snippet.code}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-[#111827] border border-white/10 hover:border-cyan-500/50 text-gray-300 hover:text-cyan-400 rounded p-2 shadow-lg"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </Dialog>
    </>
  )
}

export default PipelineHttpRun
