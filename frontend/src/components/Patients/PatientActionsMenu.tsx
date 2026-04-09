import { EllipsisVertical } from "lucide-react"
import { useState } from "react"

import type { PatientPublic } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import AssignManager from "@/components/Patients/AssignManager"
import DeletePatient from "@/components/Patients/DeletePatient"
import EditPatient from "@/components/Patients/EditPatient"

interface PatientActionsMenuProps {
  patient: PatientPublic
  isAdmin?: boolean
}

export const PatientActionsMenu = ({ patient, isAdmin = false }: PatientActionsMenuProps) => {
  const [open, setOpen] = useState(false)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <EllipsisVertical />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <EditPatient patient={patient} onSuccess={() => setOpen(false)} />
        {isAdmin && (
          <AssignManager patient={patient} onSuccess={() => setOpen(false)} />
        )}
        <DeletePatient id={patient.id} onSuccess={() => setOpen(false)} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
