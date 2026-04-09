import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { CalendarDays, FileText, Pencil, Plus } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type EncounterTranscriptPublic, TranscriptsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const transcriptFormSchema = z.object({
  text: z
    .string()
    .min(1, { message: "Transcript text is required" })
    .max(4000, { message: "Transcript must be 4,000 characters or less" }),
  encounter_date: z.string().min(1, { message: "Encounter date is required" }),
})

type TranscriptFormData = z.infer<typeof transcriptFormSchema>

function AddTranscriptDialog({ patientId }: { patientId: string }) {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<TranscriptFormData>({
    resolver: zodResolver(transcriptFormSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      text: "",
      encounter_date: new Date().toISOString().split("T")[0],
    },
  })

  const mutation = useMutation({
    mutationFn: (data: TranscriptFormData) =>
      TranscriptsService.createTranscript({
        patientId,
        requestBody: data,
      }),
    onSuccess: () => {
      showSuccessToast("Transcript added successfully")
      form.reset()
      setIsOpen(false)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["patients", patientId, "transcripts"],
      })
      queryClient.invalidateQueries({ queryKey: ["patients", patientId] })
    },
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="mr-1 h-4 w-4" />
          Add Transcript
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <Form {...form}>
          <form onSubmit={form.handleSubmit((data) => mutation.mutate(data))}>
            <DialogHeader>
              <DialogTitle>Add Encounter Transcript</DialogTitle>
              <DialogDescription>
                Record a new encounter transcript for this patient.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <FormField
                control={form.control}
                name="encounter_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Encounter Date{" "}
                      <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="text"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Transcript <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Enter encounter transcript..."
                        maxLength={4000}
                        className="min-h-[200px]"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline" disabled={mutation.isPending}>
                  Cancel
                </Button>
              </DialogClose>
              <LoadingButton type="submit" loading={mutation.isPending}>
                Save
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

function EditTranscriptDialog({
  patientId,
  transcript,
}: {
  patientId: string
  transcript: EncounterTranscriptPublic
}) {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<TranscriptFormData>({
    resolver: zodResolver(transcriptFormSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      text: transcript.text,
      encounter_date: transcript.encounter_date,
    },
  })

  const mutation = useMutation({
    mutationFn: (data: TranscriptFormData) =>
      TranscriptsService.updateTranscript({
        patientId,
        transcriptId: transcript.id,
        requestBody: data,
      }),
    onSuccess: () => {
      showSuccessToast("Transcript updated successfully")
      setIsOpen(false)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["patients", patientId, "transcripts"],
      })
      queryClient.invalidateQueries({ queryKey: ["patients", patientId] })
    },
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 shrink-0"
        onClick={() => setIsOpen(true)}
      >
        <Pencil className="h-4 w-4" />
      </Button>
      <DialogContent className="sm:max-w-lg">
        <Form {...form}>
          <form onSubmit={form.handleSubmit((data) => mutation.mutate(data))}>
            <DialogHeader>
              <DialogTitle>Edit Encounter Transcript</DialogTitle>
              <DialogDescription>
                Update the encounter transcript below.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <FormField
                control={form.control}
                name="encounter_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Encounter Date{" "}
                      <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="text"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Transcript <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Enter encounter transcript..."
                        maxLength={4000}
                        className="min-h-[200px]"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline" disabled={mutation.isPending}>
                  Cancel
                </Button>
              </DialogClose>
              <LoadingButton type="submit" loading={mutation.isPending}>
                Save
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

function formatEncounterDate(dateStr: string): string {
  const [year, month, day] = dateStr.split("-").map(Number)
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

interface EncounterTranscriptsProps {
  patientId: string
}

const EncounterTranscripts = ({ patientId }: EncounterTranscriptsProps) => {
  const { data, isLoading } = useQuery({
    queryKey: ["patients", patientId, "transcripts"],
    queryFn: () => TranscriptsService.readTranscripts({ patientId }),
  })

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Encounter Transcripts</CardTitle>
        <AddTranscriptDialog patientId={patientId} />
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div
                key={i}
                className="h-20 animate-pulse rounded-md bg-muted"
              />
            ))}
          </div>
        ) : !data?.data.length ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="rounded-full bg-muted p-3 mb-3">
              <FileText className="h-6 w-6 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground">
              No encounter transcripts recorded yet.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {data.data.map((transcript) => (
              <div key={transcript.id} className="rounded-lg border p-4">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <CalendarDays className="h-4 w-4 shrink-0" />
                    <span>{formatEncounterDate(transcript.encounter_date)}</span>
                    {transcript.created_by && (
                      <>
                        <span className="text-muted-foreground/50">·</span>
                        <span>
                          {transcript.created_by.full_name ||
                            transcript.created_by.email}
                        </span>
                      </>
                    )}
                  </div>
                  {transcript.is_editable && (
                    <EditTranscriptDialog
                      patientId={patientId}
                      transcript={transcript}
                    />
                  )}
                </div>
                <p className="text-sm whitespace-pre-wrap leading-relaxed">
                  {transcript.text}
                </p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default EncounterTranscripts
