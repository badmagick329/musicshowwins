import type { Metadata } from "next";
import { CorrectionForm } from "@/components/correction-form";

export const metadata: Metadata = {
  title: "About",
  description: "KpopWins records K-pop music show wins from 2014 onward. You can also report missing or incorrect results.",
};

export default function AboutPage() {
  return (
    <main className="page-enter mx-auto max-w-4xl px-5 pb-10 pt-10 lg:px-8 lg:pt-14">
      <section className="max-w-3xl">
        <h1 className="font-heading text-4xl font-bold tracking-tight sm:text-[44px]">About KpopWins</h1>
        <div className="mt-5 space-y-4 text-base leading-relaxed text-muted-foreground sm:text-lg">
          <p>KpopWins is a fan-made record of K-pop music show wins. It covers six weekly shows from 2014 onward.</p>
          <p>KpopWins uses Wikipedia as its source and reviews results before publication. Some older records may be incomplete or disputed.</p>
        </div>
      </section>
      <section className="mt-14" aria-labelledby="correction-heading">
        <h2 id="correction-heading" className="border-b-2 border-foreground pb-3 font-heading text-2xl font-bold">Report a correction</h2>
        <p className="mt-4 max-w-2xl leading-relaxed text-muted-foreground">Send the record and, if possible, a supporting source. Reports are reviewed and do not change public data automatically.</p>
        <CorrectionForm />
      </section>
    </main>
  );
}
