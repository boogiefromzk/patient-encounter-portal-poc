import { useSuspenseQuery } from "@tanstack/react-query"
import { Link, createFileRoute } from "@tanstack/react-router"
import { ArrowLeft, BrainCircuit, Loader2, UserCircle } from "lucide-react"
import { Fragment, Suspense, useEffect, useRef, useState } from "react"

import { PatientsService } from "@/client"
import { PatientActionsMenu } from "@/components/Patients/PatientActionsMenu"
import EncounterTranscripts from "@/components/Patients/EncounterTranscripts"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import useAuth from "@/hooks/useAuth"

function SimpleMarkdown({ text }: { text: string }) {
  return (
    <div className="text-sm leading-relaxed space-y-1">
      {text.split("\n").map((line, i) => {
        if (!line.trim()) return <br key={i} />
        const parts = line.split(/(\*\*.*?\*\*)/).map((segment, j) => {
          if (segment.startsWith("**") && segment.endsWith("**")) {
            return (
              <strong key={j} className="font-semibold">
                {segment.slice(2, -2)}
              </strong>
            )
          }
          return <Fragment key={j}>{segment}</Fragment>
        })
        return (
          <p key={i} className="my-0">
            {parts}
          </p>
        )
      })}
    </div>
  )
}

function getPatientQueryOptions(id: string) {
  return {
    queryFn: () => PatientsService.readPatient({ id }),
    queryKey: ["patients", id],
  }
}

export const Route = createFileRoute("/_layout/patients_/$id")({
  component: PatientDetailPage,
  head: () => ({
    meta: [{ title: "Patient - FastAPI Template" }],
  }),
})

function SummaryProcessingBanner() {
  return (
    <div className="flex items-center gap-2 rounded-md bg-muted/60 px-3 py-2 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span>AI summary is being generated…</span>
    </div>
  )
}

function PatientDetailContent() {
  const { id } = Route.useParams()
  const { user } = useAuth()
  const isAdmin = user?.is_superuser ?? false

  const { data: patient } = useSuspenseQuery({
    ...getPatientQueryOptions(id),
    refetchInterval: (query) => {
      return query.state.data?.summary_status === "processing" ? 2000 : false
    },
  })

  const isProcessing = patient.summary_status === "processing"
  const prevProcessing = useRef(isProcessing)
  const [justFinished, setJustFinished] = useState(false)

  useEffect(() => {
    if (prevProcessing.current && !isProcessing) {
      setJustFinished(true)
      const timer = setTimeout(() => setJustFinished(false), 3000)
      return () => clearTimeout(timer)
    }
    prevProcessing.current = isProcessing
  }, [isProcessing])

  return (
    <div className="flex flex-col gap-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/patients">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold tracking-tight truncate">
            {patient.title}
          </h1>
          <p className="text-sm text-muted-foreground">Patient record</p>
        </div>
        {isAdmin && <PatientActionsMenu patient={patient} isAdmin />}
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <BrainCircuit className="h-5 w-5 text-muted-foreground" />
            <CardTitle>AI Clinical Summary</CardTitle>
            {justFinished && (
              <span className="ml-auto text-xs font-normal text-green-600">
                Updated
              </span>
            )}
          </div>
          {patient.summary_updated_at && patient.summary_status !== "processing" && (
            <CardDescription>
              Last updated:{" "}
              {new Date(patient.summary_updated_at).toLocaleString()}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {patient.summary_status === "processing" && <SummaryProcessingBanner />}
          {patient.summary ? (
            <SimpleMarkdown text={patient.summary} />
          ) : patient.summary_status !== "processing" ? (
            <p className="text-sm italic text-muted-foreground">
              No AI summary generated yet.
            </p>
          ) : null}
        </CardContent>
      </Card>

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

      <EncounterTranscripts patientId={id} />

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
