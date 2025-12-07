
import { Link } from 'react-router'
import React from 'react'

import { Pipeline, PipelineRun, Trigger } from '../types'

interface Props {
  pipeline: Pipeline
  trigger?: Trigger
  run?: PipelineRun
  className?: string
}

const Separator = () => <span className="text-gray-600">/</span>

const Breadcrumbs: React.FC<Props> = ({
  pipeline,
  trigger,
  run,
  className,
}) => {
  if (run && !trigger) {
    throw new Error()
  }

  return (
    <div className={`flex items-center gap-2 flex-wrap text-sm text-gray-400 ${className || ''}`}>
      <Link to="/" className="hover:text-neon-400 transition-colors">Pipelines</Link>
      <Separator />
      {trigger ? (
        <Link to={`/pipelines/${pipeline.id}`} className="hover:text-neon-400 transition-colors">{pipeline.name}</Link>
      ) : (
        <span className="text-gray-200">{pipeline.name}</span>
      )}

      {trigger && (
        <>
          <Separator />
          <span>Triggers</span>
          <Separator />
          {run ? (
            <Link to={`/pipelines/${pipeline.id}/triggers/${trigger.id}`} className="hover:text-neon-400 transition-colors">
              {trigger.name}
            </Link>
          ) : (
            <span className="text-gray-200">{trigger.name}</span>
          )}
        </>
      )}

      {run && trigger && (
        <>
          <Separator />
          <span>Runs</span>
          <Separator />
          <span className="text-gray-200">#{run.id}</span>
        </>
      )}
    </div>
  )
}

export default Breadcrumbs
