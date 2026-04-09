import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { Suspense } from "react"

import { PatientsService } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import AddPatient from "@/components/Patients/AddPatient"
import { getColumns } from "@/components/Patients/columns"
import PendingPatients from "@/components/Pending/PendingPatients"
import useAuth from "@/hooks/useAuth"

function getPatientsQueryOptions() {
  return {
    queryFn: () => PatientsService.readPatients({ skip: 0, limit: 100 }),
    queryKey: ["patients"],
  }
}

export const Route = createFileRoute("/_layout/patients")({
  component: Patients,
  head: () => ({
    meta: [
      {
        title: "Patients",
      },
    ],
  }),
})

function PatientsTableContent() {
  const { data: patients } = useSuspenseQuery(getPatientsQueryOptions())
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false

  if (patients.data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">No patients found</h3>
        <p className="text-muted-foreground">
          {isAdmin
            ? "Add a new patient to get started"
            : "No patients have been assigned to you yet"}
        </p>
      </div>
    )
  }

  return <DataTable columns={getColumns(isAdmin)} data={patients.data} />
}

function PatientsTable() {
  return (
    <Suspense fallback={<PendingPatients />}>
      <PatientsTableContent />
    </Suspense>
  )
}

function Patients() {
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Patients</h1>
          <p className="text-muted-foreground">
            {isAdmin ? "Create and manage patients" : "Your assigned patients"}
          </p>
        </div>
        {isAdmin && <AddPatient />}
      </div>
      <PatientsTable />
    </div>
  )
}
