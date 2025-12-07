import {Fragment} from 'react'
import {Listbox, Transition} from '@headlessui/react'
import {CheckIcon, ChevronUpDownIcon} from '@heroicons/react/20/solid'

interface Option {
    label: string
    value: string
}

interface SelectProps {
    label?: string
    value: string
    onChange: (value: string) => void
    options: Option[]
    placeholder?: string
    icon?: React.ReactNode
}

export default function Select({
                                   label,
                                   value,
                                   onChange,
                                   options,
                                   placeholder = 'Select an option',
                                   icon,
                               }: SelectProps) {
    const selectedOption = options.find((opt) => opt.value === value)

    return (
        <div className="w-full">
            {label && (
                <label className="block text-sm font-medium text-gray-400 mb-1.5">
                    {label}
                </label>
            )}
            <Listbox value={value} onChange={onChange}>
                <div className="relative">
                    <Listbox.Button
                        className="relative w-full cursor-default rounded-lg bg-[#111827]/50 border border-white/5 py-2.5 pl-4 pr-10 text-left text-sm text-gray-200 font-mono shadow-sm focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 focus:shadow-[0_0_15px_rgba(34,211,238,0.15)] transition-all">
            <span className="block truncate">
              {selectedOption ? selectedOption.label : <span className="text-gray-500">{placeholder}</span>}
            </span>
                        <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
              <ChevronUpDownIcon
                  className="h-5 w-5 text-gray-500"
                  aria-hidden="true"
              />
            </span>
                    </Listbox.Button>
                    <Transition
                        as={Fragment}
                        leave="transition ease-in duration-100"
                        leaveFrom="opacity-100"
                        leaveTo="opacity-0"
                    >
                        <Listbox.Options
                            className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md !bg-[#1f2937] border border-cyan-500/20 py-1 text-base shadow-[0_0_20px_rgba(34,211,238,0.15)] ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm custom-scrollbar">
                            {options.map((option, optionIdx) => (
                                <Listbox.Option
                                    key={optionIdx}
                                    className={({active}) =>
                                        `relative cursor-default select-none py-2 pl-10 pr-4 font-mono transition-colors ${
                                            active ? 'bg-cyan-500/10 text-cyan-400' : 'text-white'
                                        }`
                                    }
                                    value={option.value}
                                >
                                    {({selected}) => (
                                        <>
                      <span
                          className={`block truncate ${
                              selected ? 'font-bold text-cyan-400' : 'font-normal text-white'
                          }`}
                      >
                        {option.label}
                      </span>
                                            {selected ? (
                                                <span
                                                    className="absolute inset-y-0 left-0 flex items-center pl-3 text-cyan-400">
                          <CheckIcon className="h-5 w-5" aria-hidden="true"/>
                        </span>
                                            ) : null}
                                        </>
                                    )}
                                </Listbox.Option>
                            ))}
                        </Listbox.Options>
                    </Transition>
                </div>
            </Listbox>
        </div>
    )
}
