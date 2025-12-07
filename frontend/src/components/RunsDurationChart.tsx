import { AreaChart } from '@tremor/react'
import { UseQueryResult } from '@tanstack/react-query'
import { HTTPError } from 'ky'

import { PipelineRun } from '../types'
import ErrorAlert from './queries/Error'
import { ChartLoader, MetricLoader } from './queries/Loaders'

interface Props {
  query: UseQueryResult<PipelineRun[], HTTPError>
}

const dataFormatter = (number: number) => (number / 1000).toFixed(1) + ' s'

const Loader = () => (
  <div className="glass-panel rounded-2xl p-6 shadow-glass flex flex-col h-full">
    <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-1">Duration (AVG)</h2>

    <MetricLoader />

    <div className="mt-6 flex-1">
      <ChartLoader />
    </div>
  </div>
)

const RunsDurationChart: React.FC<Props> = ({ query }) => {
  if (query.isPending) {
    return <Loader />
  }

  if (query.isError) {
    return (
      <div className="glass-panel rounded-2xl p-6 shadow-glass h-full">
        <ErrorAlert query={query} />
      </div>
    )
  }

  const runs = [...query.data].reverse()
  const successfulRuns = runs.filter((run) => run.status === 'completed')

  const avgDuration =
    successfulRuns.reduce((total, current) => total + current.duration, 0) /
      successfulRuns.length || 0

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-glass flex flex-col h-full">
      <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-1">Duration (AVG)</h2>

      <div className="flex items-baseline gap-2 mb-6">
        <span className="text-4xl font-bold text-white tracking-tight">
          {dataFormatter(avgDuration).replace(' s', '')}
        </span>
        <span className="text-lg font-medium text-neon-400">s</span>
      </div>

      <div className="flex-1 min-h-[120px] w-full">
        <AreaChart
          data={successfulRuns}
          index="id"
          categories={['duration']}
          colors={['cyan']}
          valueFormatter={dataFormatter}
          yAxisWidth={40}
          showLegend={false}
          showGridLines={false}
          showXAxis={false}
          showYAxis={false}
          autoMinValue
          className="h-full w-full"
          curveType="monotone"
        />
      </div>
    </div>
  )
}

export default RunsDurationChart
