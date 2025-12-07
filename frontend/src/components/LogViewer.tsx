import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Color,
  MultiSelect,
  MultiSelectItem,
} from '@tremor/react'
import { BarsArrowDownIcon } from '@heroicons/react/24/outline'
import { createRef, useCallback, useEffect, useState } from 'react'


import { getLogs } from '@/repository'
import { socket } from '@/socket'
import { LogEntry, LogLevel, Pipeline, PipelineRun } from '@/types'
import { formatNumber, formatTime, getTasksColors } from '@/utils'
import TracebackInfoDialog from './TracebackInfoDialog'
import ScraperLogsViewer from './ScraperLogsViewer'

interface Props {
  pipeline: Pipeline
  run: PipelineRun
}

/**
 * If the user scrolls to the bottom and arrives
 * that close to the bottom then the scroll lock is
 * activated.
 */
const SCROLL_LOCK_THRESHOLD = 30

const LOG_LEVELS_COLORS: Record<LogLevel, Color> = {
  DEBUG: 'slate',
  INFO: 'sky',
  WARNING: 'amber',
  ERROR: 'rose',
}

interface FilterType {
  levels: string[]
  tasks: string[]
}

const LogViewer: React.FC<Props> = ({ pipeline, run }) => {
  const [filter, setFilter] = useState<FilterType>({ levels: [], tasks: [] })
  const [scrollToBottom, setScrollToBottom] = useState(true)
  const queryClient = useQueryClient()

  const tableRef = createRef<HTMLTableElement>()

  const query = useQuery(getLogs(run.id))

  const onWsMessage = useCallback(
    (message: string) => {
      queryClient.setQueryData<LogEntry[]>(['logs', run.id], (oldLogs = []) => {
        const log: LogEntry = JSON.parse(message)
        log.id = oldLogs.length
        log.timestamp = new Date(log.timestamp)
        return [...oldLogs, log]
      })
    },
    [run.id]
  )

  const onMouseScroll = useCallback(
    (e: Event) => {
      const element = tableRef.current?.parentElement
      if (!element) {
        return
      }

      const event = e as WheelEvent

      // Add deltaY as the scrollTop doesn't include it at this point
      let scrollBottom = Math.max(
        element.scrollTop + element.clientHeight + event.deltaY,
        0
      )

      scrollBottom = Math.min(scrollBottom, element.scrollHeight)

      const userScrolledToBottom =
        element.scrollHeight - scrollBottom < SCROLL_LOCK_THRESHOLD

      setScrollToBottom(userScrolledToBottom)
    },
    [tableRef]
  )

  useEffect(() => {
    tableRef.current?.parentElement?.addEventListener('wheel', onMouseScroll)

    return () => {
      tableRef.current?.parentElement?.removeEventListener(
        'wheel',
        onMouseScroll
      )
    }
  }, [tableRef])

  useEffect(() => {
    if (scrollToBottom) {
      const element = tableRef.current?.parentElement
      element?.scrollTo({ top: element.scrollHeight, behavior: 'smooth' })
    }
  })

  useEffect(() => {
    socket.on(`logs.${run.id}`, onWsMessage)

    return () => {
      socket.off(`logs.${run.id}`, onWsMessage)
    }
  }, [])

  const onFilterChange = useCallback((newFilter: Partial<FilterType>) => {
    setFilter((currentFilter) => ({ ...currentFilter, ...newFilter }))
  }, [])

  if (query.isPending) {
    return <div>Loading...</div>
  }

  if (query.isError) {
    return <div>Error loading logs</div>
  }

  const logs = query.data.filter((log) => {
    return (
      (filter.levels.length === 0 || filter.levels.includes(log.level)) &&
      (filter.tasks.length === 0 || filter.tasks.includes(log.task))
    )
  })

  const tasksColors = getTasksColors(pipeline.tasks)

  const hasLiveLogs = ['running', 'pending'].includes(run.status)

  return (
    <div className="flex flex-col h-full">
      <div className="p-6 border-b border-white/5">
        <h2 className="text-lg font-semibold text-white mb-6">Pipeline Logs</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">Tasks</label>
            <MultiSelect
              className="mt-1 z-20"
              onValueChange={(tasks) => {
                onFilterChange({ tasks })
              }}
            >
              {pipeline.tasks.map((task) => (
                <MultiSelectItem value={task.id} key={task.id}>
                  {task.name}
                </MultiSelectItem>
              ))}
            </MultiSelect>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">Log level</label>
            <MultiSelect
              className="mt-1 z-20"
              onValueChange={(levels) => {
                onFilterChange({ levels })
              }}
            >
              {Object.keys(LOG_LEVELS_COLORS).map((level) => (
                <MultiSelectItem value={level} key={level} />
              ))}
            </MultiSelect>
          </div>

          {hasLiveLogs && (
            <div className="flex items-end justify-end pb-1">
              <div className="flex items-center gap-3 bg-dark-900/50 rounded-lg px-3 py-2 border border-white/5">
                <button
                  onClick={() => setScrollToBottom(!scrollToBottom)}
                  className={`p-1.5 rounded-md transition-colors ${
                    scrollToBottom ? 'bg-indigo-500/20 text-indigo-400' : 'text-gray-500 hover:text-gray-300'
                  }`}
                  title="Automatically scroll to the latest logs"
                >
                  <BarsArrowDownIcon className="w-5 h-5" />
                </button>

                <div className="flex items-center gap-2">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-indigo-500"></span>
                  </span>
                  <span className="text-sm font-medium text-indigo-300">Live logs</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col min-h-[400px]">
        <div className="overflow-y-auto custom-scrollbar flex-1 p-0" ref={tableRef}>
          <table className="w-full text-left border-collapse">
            <thead className="sticky top-0 bg-dark-900/95 backdrop-blur-sm z-10 shadow-sm">
              <tr>
                <th className="py-3 px-6 text-xs font-medium text-gray-400 uppercase tracking-wider w-48">Time</th>
                <th className="py-3 px-6 text-xs font-medium text-gray-400 uppercase tracking-wider w-24">Level</th>
                <th className="py-3 px-6 text-xs font-medium text-gray-400 uppercase tracking-wider w-48">Task</th>
                <th className="py-3 px-6 text-xs font-medium text-gray-400 uppercase tracking-wider">Message</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {logs.map((log, i) => {
                const duration =
                  i !== 0
                    ? log.timestamp.getTime() - logs[i - 1].timestamp.getTime()
                    : -1

                return (
                  <tr key={log.id} className="hover:bg-white/5 transition-colors group">
                    <td className="py-2 px-6 align-top">
                      <div className="font-mono text-xs text-gray-400">
                        <span title={formatTime(log.timestamp, true)}>
                          {formatTime(log.timestamp)}
                        </span>
                        {duration >= 0 && (
                          <span className="text-gray-600 ml-2 group-hover:text-gray-500 transition-colors">
                            +{formatNumber(duration)}ms
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-2 px-6 align-top">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
                          ${
                            log.level === 'ERROR'
                              ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                              : log.level === 'WARNING'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : log.level === 'INFO'
                              ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                              : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                          }
                        `}
                      >
                        {log.level}
                      </span>
                    </td>
                    <td className="py-2 px-6 align-top">
                      <div className="flex items-center gap-2">
                        <div className={`h-1.5 w-1.5 rounded-full ${tasksColors[log.task]}`} />
                        <span className="text-sm text-gray-300 truncate max-w-[150px]">{log.task}</span>
                      </div>
                    </td>
                    <td className="py-2 px-6 align-top">
                      <div className={`text-sm font-mono whitespace-pre-wrap break-words ${!log.task ? 'text-gray-500 italic' : 'text-gray-300'}`}>
                        {log.message}
                      </div>
                      {log.exc_info && (
                        <div className="mt-2">
                          <TracebackInfoDialog logEntry={log} />
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="p-6 border-t border-white/5 bg-dark-900/30">
        <h3 className="text-sm font-medium text-white mb-1">Scraper Log Files</h3>
        <p className="text-xs text-gray-500 mb-4">
          Detailed logs from the scraper execution
        </p>
        <ScraperLogsViewer runId={run.id} />
      </div>
    </div>
  )
}

export default LogViewer
