import { useSuspenseQuery } from "@tanstack/react-query"
import { Link, createFileRoute } from "@tanstack/react-router"
import { ArrowLeft, UserCircle } from "lucide-react"
import { Suspense } from "react"

import { ItemsService } from "@/client"
import EditItem from "@/components/Items/EditItem"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth from "@/hooks/useAuth"

function getPatientQueryOptions(id: string) {
  return {
    queryFn: () => ItemsService.readItem({ id }),
    queryKey: ["items", id],
  }
}

export const Route = createFileRoute("/_layout/items_/$id")({
  component: PatientDetailPage,
  head: () => ({
    meta: [{ title: "Patient - FastAPI Template" }],
  }),
})

function PatientDetailContent() {
  const { id } = Route.useParams()
  const { data: patient } = useSuspenseQuery(getPatientQueryOptions(id))
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/items">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold tracking-tight truncate">
            {patient.title}
          </h1>
          <p className="text-sm text-muted-foreground">Patient record</p>
        </div>
        {isAdmin && (
          <EditItem
            item={patient}
            onSuccess={() => {}}
          />
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Medical History</CardTitle>
        </CardHeader>
        <CardContent>
          {patient.description ? (
            <p className="text-sm whitespace-pre-wrap leading-relaxed">
              {patient.description}
            </p>
          ) : (
            <p className="text-sm italic text-muted-foreground">
              No medical history recorded.
            </p>
          )}
        </CardContent>
      </Card>

      {patient.owner && (
        <Card>
          <CardHeader>
            <CardTitle>Clinician</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-muted p-2">
                <UserCircle className="h-6 w-6 text-muted-foreground" />
              </div>
              <div>
                {patient.owner.full_name && (
                  <p className="font-medium text-sm">{patient.owner.full_name}</p>
                )}
                <p className="text-sm text-muted-foreground">
                  {patient.owner.email}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function PatientDetailSkeleton() {
  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <Skeleton className="size-9 rounded-md" />
        <div className="flex flex-col gap-1">
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-4 w-24" />
        </div>
      </div>
      <Skeleton className="h-48 rounded-xl" />
    </div>
  )
}

function PatientDetailPage() {
  return (
    <Suspense fallback={<PatientDetailSkeleton />}>
      <PatientDetailContent />
    </Suspense>
  )
}
