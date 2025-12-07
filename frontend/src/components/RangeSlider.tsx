import React, { createRef } from 'react'

interface Props
  extends Omit<
    React.InputHTMLAttributes<HTMLInputElement>,
    'type' | 'onInput'
  > {
  label?: string
}

const RangeSlider: React.FC<Props> = ({ label, ...props }) => {
  const output = createRef<HTMLOutputElement>()
  const inputRef = createRef<HTMLInputElement>()

  const updateProgress = (el: HTMLInputElement) => {
    const min = parseFloat(el.min || '0')
    const max = parseFloat(el.max || '100')
    const val = parseFloat(el.value || '0')
    const percentage = ((val - min) * 100) / (max - min)
    el.style.background = `linear-gradient(to right, #22d3ee 0%, #22d3ee ${percentage}%, rgba(255,255,255,0.1) ${percentage}%, rgba(255,255,255,0.1) 100%)`
  }

  // Initialize progress on mount
  React.useEffect(() => {
    if (inputRef.current) {
      updateProgress(inputRef.current)
    }
  }, [])

  return (
    <div className="w-full">
      <style>{`
        input[type=range]::-webkit-slider-thumb {
          -webkit-appearance: none;
          height: 16px;
          width: 16px;
          border-radius: 50%;
          background: #22d3ee;
          cursor: pointer;
          margin-top: -6px;
          box-shadow: 0 0 10px rgba(34, 211, 238, 0.5);
          border: 2px solid #0a0e17;
          position: relative;
          z-index: 20;
        }
        input[type=range]::-webkit-slider-runnable-track {
          width: 100%;
          height: 4px;
          cursor: pointer;
          background: transparent;
          border-radius: 2px;
          border: none;
        }
      `}</style>
      
      <input
        ref={inputRef}
        type="range"
        onInput={(event) => {
          const target = event.target as HTMLInputElement
          if (output.current) {
            output.current.value = target.value
          }
          updateProgress(target)
        }}
        className="w-full appearance-none h-1 rounded-full bg-white/10 focus:outline-none cursor-pointer"
        {...props}
      />

      <div className="flex justify-between items-end mt-2 text-xs font-mono text-gray-500">
        <div className="flex flex-col items-center">
          <div className="h-1.5 w-px bg-gray-700 mb-1" />
          <span>{props.min}</span>
        </div>

        <div className="flex flex-col items-center -translate-y-1">
          <output
            ref={output}
            className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-bold shadow-[0_0_10px_rgba(34,211,238,0.15)]"
          >
            {props.defaultValue}
          </output>
        </div>

        <div className="flex flex-col items-center">
          <div className="h-1.5 w-px bg-gray-700 mb-1" />
          <span>{props.max}</span>
        </div>
      </div>
    </div>
  )
}

export default RangeSlider
