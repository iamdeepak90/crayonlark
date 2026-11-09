import Link from "next/link";
import { PageHeader } from "@/components/site/PageHeader";
import { pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "How we make our books",
  description: "How Crayonlark coloring books are made: ideas, artwork created with the help of AI tools, a person checking every page, and print-ready files.",
  path: "/how-we-make-our-books",
});

const STEPS = [
  {
    t: "1. An idea kids will love",
    d: "We pick a theme and an age range, then plan the scenes: what goes on each page and how much detail suits that age.",
  },
  {
    t: "2. Artwork made with AI tools",
    d: "We use AI image tools to create first drafts of the line art from our own scene descriptions. Never in the style of a living artist, and never with famous characters or brands.",
  },
  {
    t: "3. A person checks every page",
    d: "Every picture is reviewed by hand. Anything unclear, odd or not right for children is thrown out. The rest is cleaned up so the lines are crisp and bold.",
  },
  {
    t: "4. Activities and print checks",
    d: "We add mazes, dot-to-dot, tracing and puzzles with answer keys, then check page sizes, margins and print resolution before anything is published.",
  },
  {
    t: "5. Paperback and printable",
    d: "The finished book goes to Amazon as a paperback and to Etsy as a printable PDF in Letter and A4.",
  },
];

export default function HowWeMakePage() {
  return (
    <div className="mx-auto max-w-4xl px-5 py-14 sm:py-20">
      <PageHeader
        eyebrow="Our process"
        title="How we make our books"
        intro="We think you should know exactly how the pages your kids color are made. Here is our process, start to finish."
      />
      <ol className="mt-12 space-y-4">
        {STEPS.map((s) => (
          <li key={s.t} className="rounded-3xl bg-white p-7 ring-1 ring-line">
            <h2 className="font-display text-xl font-semibold">{s.t}</h2>
            <p className="mt-2 leading-relaxed text-muted">{s.d}</p>
          </li>
        ))}
      </ol>
      <div className="mt-12 rounded-3xl bg-sun-50 p-7 ring-1 ring-sun-100">
        <h2 className="font-display text-xl font-semibold">Our promise about AI</h2>
        <p className="mt-2 leading-relaxed text-muted">
          Our books are designed by Crayonlark with the help of AI tools, then edited and checked by a person. They are not hand-drawn, and we will never
          say they are. Every book and printable listing states which parts were made with AI tools.
        </p>
        <p className="mt-4 text-sm">
          Questions? <Link href="/contact" className="font-semibold underline underline-offset-4">Get in touch</Link> or read the{" "}
          <Link href="/faq" className="font-semibold underline underline-offset-4">FAQ</Link>.
        </p>
      </div>
    </div>
  );
}
