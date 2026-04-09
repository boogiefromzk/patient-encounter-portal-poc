import type { ColumnDef } from "@tanstack/react-table"
import { Link } from "@tanstack/react-router"

import type { PatientPublic } from "@/client"
import { cn } from "@/lib/utils"
import { PatientActionsMenu } from "./PatientActionsMenu"

const baseColumns: ColumnDef<PatientPublic>[] = [
  {
    accessorKey: "title",
    header: "Full Name",
    cell: ({ row }) => (
      <Link
        to="/patients/$id"
        params={{ id: row.original.id }}
        className="font-medium hover:underline"
      >
        {row.original.title}
      </Link>
    ),
  },
  {
    accessorKey: "description",
    header: "Medical History",
    cell: ({ row }) => {
      const description = row.original.description
      return (
        <span
          className={cn(
            "max-w-sm truncate block text-muted-foreground",
            !description && "italic",
          )}
        >
          {description || "No medical history"}
        </span>
      )
    },
  },
]

const managerColumn: ColumnDef<PatientPublic> = {
  id: "clinician",
  header: "Clinician",
  cell: ({ row }) => {
    const owner = row.original.owner
    if (!owner) {
      return <span className="italic text-muted-foreground">Unassigned</span>
    }
    return (
      <div className="flex flex-col">
        {owner.full_name && (
          <span className="font-medium text-sm">{owner.full_name}</span>
        )}
        <span className="text-xs text-muted-foreground">{owner.email}</span>
      </div>
    )
  },
}

export function getColumns(isAdmin: boolean): ColumnDef<PatientPublic>[] {
  const actionsColumn: ColumnDef<PatientPublic> = {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <PatientActionsMenu patient={row.original} isAdmin={isAdmin} />
      </div>
    ),
  }

  if (isAdmin) {
    return [...baseColumns, managerColumn, actionsColumn]
  }
  return [...baseColumns, actionsColumn]
}

export const columns = getColumns(false)
