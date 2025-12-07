import { QuestionMarkCircleIcon } from '@heroicons/react/24/outline'
import React, { useState, useCallback } from 'react'

import Input from './Input'
import Select from './Select'

interface Props {
  errors?: Record<string, string>
}

const TIME_RANGE_OPTIONS = [
  { label: 'All Time', value: 'AllTime' },
  { label: 'Today', value: 'Today' },
  { label: 'Yesterday', value: 'Yesterday' },
  { label: 'This Week', value: 'ThisWeek' },
  { label: 'Last Week', value: 'LastWeek' },
  { label: 'This Month', value: 'ThisMonth' },
  { label: 'Last Month', value: 'LastMonth' },
  { label: 'This Quarter', value: 'ThisQuarter' },
  { label: 'Last Quarter', value: 'LastQuarter' },
  { label: 'This Year', value: 'ThisYear' },
  { label: 'Last Year', value: 'LastYear' },
  { label: 'Last 7 Days', value: 'Last7Days' },
  { label: 'Last 14 Days', value: 'Last14Days' },
  { label: 'Last 30 Days', value: 'Last30Days' },
  { label: 'Last 60 Days', value: 'Last60Days' },
  { label: 'Last 90 Days', value: 'Last90Days' },
  { label: 'Custom Date Range...', value: 'custom' },
]

const FlowMeterParamsForm: React.FC<Props> = React.memo(({ errors = {} }) => {
  const [timeRangeOption, setTimeRangeOption] = useState<string>('ThisQuarter')

  const isCustomRange = timeRangeOption === 'custom'

  const handleTimeRangeChange = useCallback((value: string) => {
    setTimeRangeOption(value)
  }, [])

  return (
    <div className="flex flex-col gap-5">
      {/* Max Pages */}
      <div>
        <div className="flex justify-between items-center mb-1.5">
          <label className="text-sm font-medium text-gray-400">Max Pages</label>
          <div className="group relative flex items-center">
            <QuestionMarkCircleIcon className="w-4 h-4 text-gray-500 hover:text-gray-300 transition-colors cursor-help" />
            <div className="absolute right-0 bottom-full mb-2 hidden group-hover:block w-48 p-2 bg-gray-800 text-xs text-gray-300 rounded shadow-lg z-50 border border-white/10">
              Maximum number of pages to fetch (None = all pages)
            </div>
          </div>
        </div>
        <Input
          name="max_pages"
          type="number"
          defaultValue="100"
          min={1}
          error={errors['max_pages']}
        />
      </div>

      {/* Delay Between Requests */}
      <div>
        <div className="flex justify-between items-center mb-1.5">
          <label className="text-sm font-medium text-gray-400">Delay Between Requests (seconds)</label>
          <div className="group relative flex items-center">
            <QuestionMarkCircleIcon className="w-4 h-4 text-gray-500 hover:text-gray-300 transition-colors cursor-help" />
            <div className="absolute right-0 bottom-full mb-2 hidden group-hover:block w-48 p-2 bg-gray-800 text-xs text-gray-300 rounded shadow-lg z-50 border border-white/10">
              Delay between API requests in seconds
            </div>
          </div>
        </div>
        <Input
          name="delay_between_requests"
          type="number"
          defaultValue="2"
          min={0}
          max={10}
          error={errors['delay_between_requests']}
        />
      </div>

      {/* Delay Between Sites */}
      <div>
        <div className="flex justify-between items-center mb-1.5">
          <label className="text-sm font-medium text-gray-400">Delay Between Sites (seconds)</label>
          <div className="group relative flex items-center">
            <QuestionMarkCircleIcon className="w-4 h-4 text-gray-500 hover:text-gray-300 transition-colors cursor-help" />
            <div className="absolute right-0 bottom-full mb-2 hidden group-hover:block w-48 p-2 bg-gray-800 text-xs text-gray-300 rounded shadow-lg z-50 border border-white/10">
              Delay between different sites in seconds
            </div>
          </div>
        </div>
        <Input
          name="delay_between_sites"
          type="number"
          defaultValue="5"
          min={0}
          max={30}
          error={errors['delay_between_sites']}
        />
      </div>

      {/* Time Range Selection */}
      <div onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-1.5">
          <label className="text-sm font-medium text-gray-400">Time Range</label>
          <div className="group relative flex items-center">
            <QuestionMarkCircleIcon className="w-4 h-4 text-gray-500 hover:text-gray-300 transition-colors cursor-help" />
            <div className="absolute right-0 bottom-full mb-2 hidden group-hover:block w-64 p-2 bg-gray-800 text-xs text-gray-300 rounded shadow-lg z-50 border border-white/10">
              Select a quick time range or choose Custom Date Range to specify exact dates
            </div>
          </div>
        </div>
        <Select
          value={timeRangeOption}
          onChange={handleTimeRangeChange}
          options={TIME_RANGE_OPTIONS}
        />
        {errors['time_range_mode'] && (
          <p className="mt-1 text-xs text-rose-400">
            {errors['time_range_mode']}
          </p>
        )}
      </div>

      {/* Custom Date Range (only shown when Custom is selected) */}
      {isCustomRange && (
        <div className="grid grid-cols-2 gap-4 p-4 rounded-lg bg-white/5 border border-white/5">
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-sm font-medium text-gray-400">From Date/Time</label>
              <div className="group relative flex items-center">
                <QuestionMarkCircleIcon className="w-4 h-4 text-gray-500 hover:text-gray-300 transition-colors cursor-help" />
                <div className="absolute right-0 bottom-full mb-2 hidden group-hover:block w-64 p-2 bg-gray-800 text-xs text-gray-300 rounded shadow-lg z-50 border border-white/10">
                  Start date/time in format: YYYY-MM-DDTHH:MM:SS
                </div>
              </div>
            </div>
            <Input
              name="custom_from"
              placeholder="2025-01-01T00:00:00"
              defaultValue=""
              error={errors['custom_from']}
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-sm font-medium text-gray-400">To Date/Time</label>
              <div className="group relative flex items-center">
                <QuestionMarkCircleIcon className="w-4 h-4 text-gray-500 hover:text-gray-300 transition-colors cursor-help" />
                <div className="absolute right-0 bottom-full mb-2 hidden group-hover:block w-64 p-2 bg-gray-800 text-xs text-gray-300 rounded shadow-lg z-50 border border-white/10">
                  End date/time in format: YYYY-MM-DDTHH:MM:SS
                </div>
              </div>
            </div>
            <Input
              name="custom_to"
              placeholder="2025-01-31T23:59:59"
              defaultValue=""
              error={errors['custom_to']}
            />
          </div>
        </div>
      )}

      {/* Hidden fields to send correct data to backend */}
      <input
        type="hidden"
        name="time_range_mode"
        value={isCustomRange ? 'custom' : 'preset'}
      />
      <input
        type="hidden"
        name="preset_value"
        value={isCustomRange ? '' : timeRangeOption}
      />
    </div>
  )
})

FlowMeterParamsForm.displayName = 'FlowMeterParamsForm'

export default FlowMeterParamsForm
