import type { ColumnDef } from "@tanstack/react-table"
import { Check, Copy } from "lucide-react"

import type { ItemPublic } from "@/client"
import { Button } from "@/components/ui/button"
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard"
import { cn } from "@/lib/utils"
import { ItemActionsMenu } from "./ItemActionsMenu"

function CopyId({ id }: { id: string }) {
  const [copiedText, copy] = useCopyToClipboard()
  const isCopied = copiedText === id

  return (
    <div className="flex items-center gap-1.5 group">
      <span className="font-mono text-xs text-muted-foreground">{id}</span>
      <Button
        variant="ghost"
        size="icon"
        className="size-6 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={() => copy(id)}
      >
        {isCopied ? (
          <Check className="size-3 text-green-500" />
        ) : (
          <Copy className="size-3" />
        )}
        <span className="sr-only">Copy ID</span>
      </Button>
    </div>
  )
}

const baseColumns: ColumnDef<ItemPublic>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <CopyId id={row.original.id} />,
  },
  {
    accessorKey: "title",
    header: "Name",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.title}</span>
    ),
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => {
      const description = row.original.description
      return (
        <span
          className={cn(
            "max-w-xs truncate block text-muted-foreground",
            !description && "italic",
          )}
        >
          {description || "No description"}
        </span>
      )
    },
  },
]

const managerColumn: ColumnDef<ItemPublic> = {
  id: "manager",
  header: "Manager",
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

export function getColumns(isAdmin: boolean): ColumnDef<ItemPublic>[] {
  const actionsColumn: ColumnDef<ItemPublic> = {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <ItemActionsMenu item={row.original} isAdmin={isAdmin} />
      </div>
    ),
  }

  if (isAdmin) {
    return [...baseColumns, managerColumn, actionsColumn]
  }
  return [...baseColumns, actionsColumn]
}

export const columns = getColumns(false)
