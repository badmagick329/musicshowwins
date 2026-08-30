import type { Metadata } from "next";
import { CorrectionForm } from "@/components/correction-form";

export const metadata: Metadata = {
  title: "About — KpopWins",
  description: "About the KpopWins archive and how to report a correction.",
};

export default function AboutPage() {
  return (
    <main className="page-enter mx-auto max-w-4xl px-5 pb-10 pt-10 lg:px-8 lg:pt-14">
      <section className="max-w-3xl">
        <h1 className="font-heading text-4xl font-bold tracking-tight sm:text-[44px]">About KpopWins</h1>
        <div className="mt-5 space-y-4 text-base leading-relaxed text-muted-foreground sm:text-lg">
          <p>KpopWins is a fan-made archive for exploring Korean music-show wins. It currently covers six weekly shows from 2014 onward.</p>
          <p>Results are compiled from Wikipedia and reviewed before they are added. Some older records may be incomplete or disputed, and corrections are welcome.</p>
        </div>
      </section>
      <section className="mt-14" aria-labelledby="correction-heading">
        <h2 id="correction-heading" className="border-b-2 border-foreground pb-3 font-heading text-2xl font-bold">Report a correction</h2>
        <p className="mt-4 max-w-2xl leading-relaxed text-muted-foreground">Spot something that needs attention? Send the record and a supporting source for review. Reports do not change the public archive automatically.</p>
        <CorrectionForm />
      </section>
    </main>
  );
}
