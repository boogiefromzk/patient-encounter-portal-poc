import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { Suspense } from "react"

import { ItemsService } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import AddItem from "@/components/Items/AddItem"
import { getColumns } from "@/components/Items/columns"
import PendingItems from "@/components/Pending/PendingItems"
import useAuth from "@/hooks/useAuth"

function getItemsQueryOptions() {
  return {
    queryFn: () => ItemsService.readItems({ skip: 0, limit: 100 }),
    queryKey: ["items"],
  }
}

export const Route = createFileRoute("/_layout/items")({
  component: Items,
  head: () => ({
    meta: [
      {
        title: "Patients - FastAPI Template",
      },
    ],
  }),
})

function ItemsTableContent() {
  const { data: items } = useSuspenseQuery(getItemsQueryOptions())
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false

  if (items.data.length === 0) {
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

  return <DataTable columns={getColumns(isAdmin)} data={items.data} />
}

function ItemsTable() {
  return (
    <Suspense fallback={<PendingItems />}>
      <ItemsTableContent />
    </Suspense>
  )
}

function Items() {
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
        {isAdmin && <AddItem />}
      </div>
      <ItemsTable />
    </div>
  )
}
