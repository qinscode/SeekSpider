
import { Dialog as HUDialog, Transition } from '@headlessui/react'
import { Fragment, PropsWithChildren, ReactNode } from 'react'

interface Props extends PropsWithChildren {
  footer?: ReactNode
  isOpen: boolean
  subtitle?: string
  title?: string
  onClose: () => any
  disableOutsideClick?: boolean
}

const Dialog: React.FC<Props> = ({
  children,
  footer,
  isOpen,
  subtitle,
  title,
  onClose,
  disableOutsideClick = false,
}) => {
  return (
    <Transition show={isOpen} as={Fragment}>
      <HUDialog
        onClose={disableOutsideClick ? () => {} : onClose}
        className="relative z-50"
      >
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div
            className="fixed inset-0 bg-[#0a0e17]/80 backdrop-blur-sm"
            aria-hidden="true"
          />
        </Transition.Child>

        <div className="fixed inset-0 flex w-screen items-center justify-center p-4">
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95 translate-y-4"
            enterTo="opacity-100 scale-100 translate-y-0"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100 translate-y-0"
            leaveTo="opacity-0 scale-95 translate-y-4"
          >
            <HUDialog.Panel className="w-full max-w-lg transform transition-all">
              <div className="bg-[#111827]/70 backdrop-blur-xl border border-white/5 rounded-2xl p-6 shadow-[0_0_50px_rgba(0,0,0,0.5)]">
                {title && (
                  <HUDialog.Title className="text-xl font-bold text-gray-100 tracking-tight">
                    {title}
                  </HUDialog.Title>
                )}

                {subtitle && (
                  <p className="mt-1 text-sm text-gray-400">
                    {subtitle}
                  </p>
                )}

                <div className={(title || subtitle) ? 'mt-6' : ''}>
                  {children}
                </div>

                {footer && (
                  <div className="flex justify-end gap-3 mt-8 pt-4 border-t border-white/5">
                    {footer}
                  </div>
                )}
              </div>
            </HUDialog.Panel>
          </Transition.Child>
        </div>
      </HUDialog>
    </Transition>
  )
}

export default Dialog
