import { useQuery } from '@tanstack/react-query'
import { Card, Text } from '@tremor/react'
import { useState } from 'react'
import { ChevronDownIcon, ChevronRightIcon } from '@heroicons/react/24/outline'

import { getScraperLog, listScraperLogs, ScraperLogFile } from '@/repository'

interface Props {
  runId: number
}

const ScraperLogsViewer: React.FC<Props> = ({ runId }) => {
  const logsQuery = useQuery(listScraperLogs(runId))
  const [expandedLog, setExpandedLog] = useState<string | null>(null)
  const [logContents, setLogContents] = useState<Record<string, string>>({})

  const handleToggle = async (filename: string) => {
    if (expandedLog === filename) {
      setExpandedLog(null)
    } else {
      setExpandedLog(filename)

      // Fetch log content if not already loaded
      if (!logContents[filename]) {
        try {
          const content = await getScraperLog(runId, filename)
          setLogContents((prev) => ({ ...prev, [filename]: content }))
        } catch (error) {
          setLogContents((prev) => ({
            ...prev,
            [filename]: `Error loading log: ${error}`,
          }))
        }
      }
    }
  }

  if (logsQuery.isPending) {
    return <Text>Loading scraper logs...</Text>
  }

  if (logsQuery.isError) {
    return null
  }

  const logs = logsQuery.data

  if (!logs || logs.length === 0) {
    return (
      <Text className="text-slate-500 italic">
        No scraper log files available for this run
      </Text>
    )
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="space-y-2">
      {logs.map((log: ScraperLogFile) => {
        const isExpanded = expandedLog === log.filename
        return (
          <Card key={log.filename} className="p-0">
            <button
              onClick={() => handleToggle(log.filename)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
            >
              <div className="flex items-center gap-2">
                {isExpanded ? (
                  <ChevronDownIcon className="h-4 w-4 text-slate-500" />
                ) : (
                  <ChevronRightIcon className="h-4 w-4 text-slate-500" />
                )}
                <Text className="font-medium">{log.filename}</Text>
              </div>
              <Text className="text-slate-500 text-sm">
                {formatFileSize(log.size)}
              </Text>
            </button>
            {isExpanded && (
              <div className="px-4 pb-4">
                <pre className="bg-slate-50 dark:bg-slate-900 p-4 rounded text-xs overflow-x-auto whitespace-pre-wrap font-mono max-h-96 overflow-y-auto border border-slate-200 dark:border-slate-700">
                  {logContents[log.filename] || 'Loading...'}
                </pre>
              </div>
            )}
          </Card>
        )
      })}
    </div>
  )
}

export default ScraperLogsViewer
