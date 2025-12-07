import { UseMutationOptions, UseQueryOptions } from '@tanstack/react-query'
import ky, { HTTPError, Options } from 'ky'

import {
  LogEntry,
  Pipeline,
  PipelineRun,
  PipelineScheduleState,

  WhoamiResponse,
} from './types'
import { JSONSchema7 } from 'json-schema'

interface BaseError {
  status: number
  data: any
}

interface Error422 extends BaseError {
  status: 422
  data: {
    detail: {
      loc: string[]
      msg: string
      type: string
    }[]
  }
}

type AllErrors = Error422

class PlomberyHttpError extends Error implements BaseError {
  data: any
  status: number

  constructor(message: string, status: number, data: AllErrors) {
    super(message)
    this.data = { data, status }
    this.status = status
  }
}

const DEFAULT_BASE_URL = import.meta.env.DEV
  ? 'http://localhost:8000/api'
  : `${window.location.protocol}//${window.location.host}/api`
const BASE_URL: string = import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL

const client = ky.create({
  prefixUrl: BASE_URL,
  credentials: 'include',
  redirect: 'follow',
  timeout: 120000, // 2 minutes
})

export const getApiUrl = (): string => BASE_URL

/**
 * Helper function to GET a JSON request
 */
const get = async <ResponseType = any>(
  url: string,
  request?: Omit<Options, 'method'>
): Promise<ResponseType> => {
  return (await client.get(url, request)).json<ResponseType>()
}

/**
 * Helper function to POST a JSON request
 */
const post = async <ResponseType = any>(
  url: string,
  request?: Options
): Promise<ResponseType> => {
  try {
    return await client.post(url, request).json<ResponseType>()
  } catch (e) {
    const error = e as HTTPError

    throw new PlomberyHttpError(
      error.message,
      error.response.status,
      await error.response.json()
    )
  }
}

export const getWebsocketUrl = () => {
  // Prefer the current origin to avoid cross-host websocket issues in proxied setups
  const apiUrl = new URL(BASE_URL)
  const originUrl = new URL(window.location.origin)

  const baseUrl =
    apiUrl.hostname === originUrl.hostname && apiUrl.port === originUrl.port
      ? apiUrl
      : originUrl

  baseUrl.pathname = apiUrl.pathname.replace(/api$/, '')

  return baseUrl
}

export const getPipelineRunUrl = (pipelineId: string) =>
  `${BASE_URL}/pipelines/${pipelineId}/run`

export const getCurrentUser = async () => {
  return await get<WhoamiResponse>('auth/whoami')
}

export const logout = async () => {
  await post('auth/logout')
}

export const login = async (email: string, password: string) => {
  return await post<{ user: { email: string; name: string }; message: string }>(
    'auth/login',
    {
      json: { email, password },
    }
  )
}

export const getAuthProviders = (): UseQueryOptions<
  { id: string; name: string; redirect_uri: string }[],
  HTTPError
> => ({
  queryKey: ['auth-providers'],
  queryFn: async () => {
    return await get('auth/providers')
  },
})

/**
 * Pipelines
 */



export const listPipelines = (): UseQueryOptions<Pipeline[], HTTPError> => ({
  queryKey: ['pipelines'],
  queryFn: async () => {
    const pipelines = await get<Pipeline[]>('pipelines/')

    pipelines.forEach((pipeline) => {
      pipeline.triggers.forEach((trigger) => {
        if (trigger.next_fire_time) {
          trigger.next_fire_time = new Date(trigger.next_fire_time)
        }
      })
    })

    return pipelines.map(
      (pipeline) =>
        new Pipeline(
          pipeline.id,
          pipeline.name,
          pipeline.description,
          pipeline.tasks,
          pipeline.triggers,
          (pipeline as any).schedule_enabled ?? true
        )
    )
  },
  initialData: [],
})

export const getPipeline = (
  pipelineId: string
): UseQueryOptions<Pipeline, HTTPError> => ({
  queryKey: ['pipeline', pipelineId],
  queryFn: async () => {
    const pipeline = await get<Pipeline>(`pipelines/${pipelineId}`)

    pipeline.triggers.forEach((trigger) => {
      if (trigger.next_fire_time) {
        trigger.next_fire_time = new Date(trigger.next_fire_time)
      }
    })

    return new Pipeline(
      pipeline.id,
      pipeline.name,
      pipeline.description,
      pipeline.tasks,
      pipeline.triggers,
      (pipeline as any).schedule_enabled ?? true
    )
  },
  initialData: new Pipeline('', '', '', [], [], true),
  enabled: !!pipelineId,
})

export const getPipelineInputSchema = (
  pipelineId: string
): UseQueryOptions<JSONSchema7, HTTPError> => ({
  queryKey: ['pipeline-input', pipelineId],
  queryFn: async () => {
    return await get(`pipelines/${pipelineId}/input-schema`)
  },
})

/**
 * Runs
 */

export const listRuns = (
  pipelineId?: string,
  triggerId?: string
): UseQueryOptions<PipelineRun[], HTTPError> => ({
  queryKey: ['runs', pipelineId, triggerId],
  queryFn: async () => {
    const params = {
      pipeline_id: pipelineId ?? '',
      trigger_id: triggerId ?? '',
    }

    const runs = await get<any[]>('runs/', {
      searchParams: params,
    })

    runs.forEach((run) => {
      run.start_time = new Date(run.start_time)
    })

    return runs as PipelineRun[]
  },
  initialData: [],
})

export const getRun = (
  pipelineId: string,
  triggerId: string,
  runId: number
): UseQueryOptions<PipelineRun, HTTPError> => ({
  queryKey: ['runs', pipelineId, triggerId, runId],
  queryFn: async () => {
    const run = await get(`runs/${runId}`)
    run.start_time = new Date(run.start_time)

    return run as PipelineRun
  },
  enabled: !!(pipelineId && triggerId && runId),
})

export const getLogs = (
  runId: number
): UseQueryOptions<LogEntry[], HTTPError> => ({
  queryKey: ['logs', runId],
  queryFn: async () => {
    const rawLogs = await client.get(`runs/${runId}/logs`).text()

    if (!rawLogs) {
      return []
    }

    // Logs data is in JSONL format (1 JSON object per line)
    return rawLogs.split('\n').map((line, i) => {
      const parsed = JSON.parse(line)
      // Add a unique id to be used as key for React
      parsed.id = i
      parsed.timestamp = new Date(parsed.timestamp)
      return parsed
    })
  },
  enabled: !!runId,
  initialData: [],
})

export const getRunDataUrl = (runId: number, taskId: string) =>
  `runs/${runId}/data/${taskId}`

export const getRunData = (
  runId: number,
  taskId: string
): UseQueryOptions<any, HTTPError> => ({
  queryKey: ['getRunData', { runId, taskId }],
  queryFn: async () => {
    return await get(getRunDataUrl(runId, taskId))
  },
})

export const runPipeline = (
  pipelineId: string,
  triggerId?: string
): UseMutationOptions<
  PipelineRun,
  PlomberyHttpError,
  Record<string, any> | void
> => ({
  async mutationFn(params) {
    return await post<PipelineRun>(`pipelines/${pipelineId}/run`, {
      json: {
        trigger_id: triggerId,
        params,
        reason: 'web',
      },
    })
  },
})



export const updatePipelineScheduleState = (
  pipelineId: string
): UseMutationOptions<
  PipelineScheduleState,
  PlomberyHttpError,
  boolean
> => ({
  mutationFn: async (scheduleEnabled: boolean) => {
    return await post<PipelineScheduleState>(
      `pipelines/${pipelineId}/schedule`,
      {
        json: { schedule_enabled: scheduleEnabled },
      }
    )
  },
})

export const getLatestRelease = (): UseQueryOptions<{
  tag_name: string
  prerelease: boolean
}> => ({
  queryKey: ['gh', 'latest-release'],
  queryFn: async () => {
    return await ky
      .get(
        'https://api.github.com/repos/lucafaggianelli/plombery/releases/latest'
      )
      .json<{ tag_name: string; prerelease: boolean }>()
  },
})

/**
 * Scraper Logs
 */

export interface ScraperLogFile {
  filename: string
  size: number
  modified: number
}

export const listScraperLogs = (
  runId: number
): UseQueryOptions<ScraperLogFile[], HTTPError> => ({
  queryKey: ['scraper-logs', runId],
  queryFn: async () => {
    return await get<ScraperLogFile[]>(`runs/${runId}/scraper-logs`)
  },
  enabled: !!runId,
  initialData: [],
})

export const getScraperLog = async (
  runId: number,
  filename: string
): Promise<string> => {
  return await client.get(`runs/${runId}/scraper-logs/${filename}`).text()
}
