"use client";

import { useMutation } from "@tanstack/react-query";
import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { submitCorrection } from "@/lib/api-browser";
import type { CorrectionReport } from "@/lib/api-shared";

const emptyReport: CorrectionReport = {
  page_or_record: "",
  correction: "",
  supporting_source: "",
  contact: "",
  website: "",
};

type ReportErrors = Partial<Record<keyof CorrectionReport, string>>;

export function validateCorrection(report: CorrectionReport): ReportErrors {
  const errors: ReportErrors = {};
  if (report.page_or_record.length > 300) errors.page_or_record = "Use 300 characters or fewer.";
  if (!report.correction.trim()) errors.correction = "Enter your feedback.";
  else if (report.correction.length > 1000) errors.correction = "Use 1,000 characters or fewer.";
  if (report.contact.length > 200) errors.contact = "Use 200 characters or fewer.";
  else if (report.contact.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(report.contact.trim())) errors.contact = "Enter a valid email address.";
  return errors;
}

const fieldClass = "mt-2 min-h-11 w-full border border-input bg-card px-3 py-2 text-foreground outline-none focus:border-ring disabled:bg-muted";

export function CorrectionForm() {
  const [report, setReport] = useState(emptyReport);
  const [errors, setErrors] = useState<ReportErrors>({});
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const sendingRef = useRef(false);
  const pageRef = useRef<HTMLInputElement>(null);
  const correctionRef = useRef<HTMLTextAreaElement>(null);
  const contactRef = useRef<HTMLInputElement>(null);
  const statusRef = useRef<HTMLParagraphElement>(null);

  const mutation = useMutation({
    mutationFn: async (nextReport: CorrectionReport) => {
      try {
        await submitCorrection(nextReport);
        return true;
      } catch {
        return false;
      }
    },
    onSuccess: (accepted) => {
      sendingRef.current = false;
      if (!accepted) {
        setStatus("error");
        queueMicrotask(() => statusRef.current?.focus());
        return;
      }
      setReport(emptyReport);
      setErrors({});
      setStatus("success");
      queueMicrotask(() => statusRef.current?.focus());
    },
    onError: () => {
      sendingRef.current = false;
      setStatus("error");
      queueMicrotask(() => statusRef.current?.focus());
    },
  });

  function update(event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    const key = event.target.name as keyof CorrectionReport;
    setReport((current) => ({ ...current, [key]: event.target.value }));
    setErrors((current) => ({ ...current, [key]: undefined }));
    if (status !== "idle") setStatus("idle");
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sendingRef.current) return;
    const nextErrors = validateCorrection(report);
    setErrors(nextErrors);
    setStatus("idle");
    const firstError = (Object.keys(nextErrors) as (keyof CorrectionReport)[])[0];
    if (firstError) {
      const refs = { page_or_record: pageRef, correction: correctionRef, contact: contactRef };
      if (firstError !== "website" && firstError !== "supporting_source") refs[firstError].current?.focus();
      return;
    }
    sendingRef.current = true;
    mutation.mutate({ ...report, page_or_record: report.page_or_record.trim(), correction: report.correction.trim(), supporting_source: report.supporting_source.trim(), contact: report.contact.trim() });
  }

  return (
    <form className="mt-6 space-y-5 border-2 border-foreground bg-card p-5 shadow-[4px_4px_0_var(--section-ink)] sm:p-6" onSubmit={submit} noValidate>
      <div>
        <label htmlFor="correction" className="font-bold">Your feedback <span aria-hidden="true">*</span></label>
        <textarea ref={correctionRef} id="correction" name="correction" value={report.correction} onChange={update} required maxLength={1000} rows={6} aria-invalid={Boolean(errors.correction)} aria-describedby={errors.correction ? "correction-error" : undefined} className={fieldClass} />
        {errors.correction && <p id="correction-error" className="mt-1 text-sm text-destructive">{errors.correction}</p>}
      </div>
      <div>
        <label htmlFor="page-or-record" className="font-bold">Related page or link <span className="font-normal text-muted-foreground">(optional)</span></label>
        <input ref={pageRef} id="page-or-record" name="page_or_record" value={report.page_or_record} onChange={update} maxLength={300} aria-invalid={Boolean(errors.page_or_record)} aria-describedby={errors.page_or_record ? "page-or-record-error" : undefined} className={fieldClass} />
        {errors.page_or_record && <p id="page-or-record-error" className="mt-1 text-sm text-destructive">{errors.page_or_record}</p>}
      </div>
      <div>
        <label htmlFor="contact" className="font-bold">Email, if you&apos;d like a reply <span className="font-normal text-muted-foreground">(optional)</span></label>
        <input ref={contactRef} id="contact" name="contact" type="email" autoComplete="email" value={report.contact} onChange={update} maxLength={200} aria-describedby={errors.contact ? "contact-error" : undefined} className={fieldClass} />
        {errors.contact && <p id="contact-error" className="mt-1 text-sm text-destructive">{errors.contact}</p>}
      </div>
      <div className="absolute -left-[10000px] top-auto size-px overflow-hidden" aria-hidden="true">
        <label htmlFor="website">Website</label>
        <input id="website" name="website" value={report.website} onChange={update} tabIndex={-1} autoComplete="off" />
      </div>
      <button type="submit" disabled={mutation.isPending} className="inline-flex w-full sm:w-auto min-h-11 items-center justify-center border border-foreground bg-brand-pink px-5 font-bold text-white shadow-[2px_2px_0_var(--foreground)] transition-transform hover:-translate-y-0.5 disabled:translate-y-0 disabled:opacity-60">
        {mutation.isPending ? "Sending…" : "Send feedback"}
      </button>
      {status === "success" && <p ref={statusRef} tabIndex={-1} role="status" className="border-l-4 border-success bg-muted px-4 py-3 text-sm">Thanks! Your feedback was sent.</p>}
      {status === "error" && <p ref={statusRef} tabIndex={-1} role="alert" className="border-l-4 border-destructive bg-danger-surface px-4 py-3 text-sm">We couldn&apos;t send your feedback. Your text is still here. Try again in a moment.</p>}
    </form>
  );
}
