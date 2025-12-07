import { useQuery } from '@tanstack/react-query'
import { listRuns } from '@/repository'

import PipelinesList from '@/components/PipelinesList'
import RunsList from '@/components/RunsList'
import Navbar from '@/components/Navbar'


const HomePage: React.FC = () => {
  const runsQuery = useQuery(listRuns())


  return (
    <div className="text-gray-300 antialiased h-screen flex flex-col overflow-hidden font-sans bg-[#0a0e17]">
      <Navbar />

      <main className="flex-1 flex gap-6 p-6 overflow-hidden max-w-[1800px] mx-auto w-full relative z-10">
        <aside className="w-[420px] flex flex-col gap-4 shrink-0 overflow-y-auto custom-scrollbar pr-2">
          <PipelinesList />
        </aside>

        <section className="flex-1 flex flex-col overflow-hidden">
          <RunsList query={runsQuery} />
        </section>
      </main>


    </div>
  )
}

export default HomePage
