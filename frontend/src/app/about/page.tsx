import type { Metadata } from "next";
import { CorrectionForm } from "@/components/correction-form";
import { pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "About",
  description: "KpopWins records K-pop music show wins from 2014 onward. Share feedback and suggestions for the archive.",
  path: "/about",
});

export default function AboutPage() {
  return (
    <main className="page-enter mx-auto max-w-4xl px-5 pb-10 pt-10 lg:px-8 lg:pt-14">
      <section className="max-w-3xl">
        <h1 className="font-heading text-4xl font-bold tracking-tight sm:text-[44px]">About KpopWins</h1>
        <p className="mt-5 text-base leading-relaxed text-muted-foreground sm:text-lg">KpopWins is a fan-made record of K-pop music show wins. It covers six weekly shows from 2014 onward. KpopWins uses Wikipedia as its source and reviews results before publication.</p>
        <p className="mt-4 text-base leading-relaxed text-muted-foreground">We maintain the archive, add new results, and expand video coverage. Your feedback helps us decide what to improve next.</p>
      </section>
      <section id="feedback" className="mt-14 scroll-mt-6" aria-labelledby="feedback-heading">
        <h2 id="feedback-heading" className="border-b-2 border-foreground pb-3 font-heading text-2xl font-bold">Share feedback</h2>
        <p className="mt-4 max-w-2xl leading-relaxed text-muted-foreground">Have an idea, found something confusing, or wish the site did something differently? Tell us below. Corrections and missing video links are welcome too.</p>
        <CorrectionForm />
      </section>
    </main>
  );
}
