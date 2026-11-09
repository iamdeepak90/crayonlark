import Link from "next/link";
import { ButtonLink } from "@/components/site/ButtonLink";
import { PageHeader } from "@/components/site/PageHeader";
import { AGE_GROUPS } from "@/lib/content";
import { pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "For parents & teachers",
  description: "How to pick the right Crayonlark book for each age, and how to use our printables at home and in one classroom.",
  path: "/parents-and-teachers",
});

const SKILLS = [
  { t: "Fine motor skills", d: "Holding a crayon and stopping at a line strengthens small hand muscles.", bar: "bg-sun-400" },
  { t: "Focus & patience", d: "Finishing a page is a small, satisfying goal that builds attention.", bar: "bg-coral-500" },
  { t: "Early literacy & numbers", d: "Tracing, word searches and dot-to-dot practise letters and counting.", bar: "bg-coral-500" },
  { t: "Calm, screen-free time", d: "A quiet activity for after school, travel or rainy afternoons.", bar: "bg-coral-500" },
];

export default function ParentsTeachersPage() {
  return (
    <div className="mx-auto max-w-6xl px-5 py-14 sm:py-20">
      <PageHeader
        eyebrow="Parents & teachers"
        title="Simple pages that grow with your kids"
        intro="Our books are designed for real homes and real classrooms: clear lines, the right amount of detail for each age, and pages printed on one side only."
      />

      <section aria-labelledby="ages" className="mt-16">
        <h2 id="ages" className="font-display text-2xl font-semibold">Choosing by age</h2>
        <div className="mt-6 grid gap-5 sm:grid-cols-3">
          {AGE_GROUPS.map((g) => (
            <Link key={g.title} href={`/books?age=${g.age}`} className={`group rounded-lg p-7 transition hover:shadow-soft ${g.bg}`}>
              <p className={`text-sm font-semibold ${g.eyebrow}`}>{g.label}</p>
              <h3 className="mt-2 font-display text-xl font-semibold">{g.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{g.text}</p>
              <span className="mt-6 inline-flex items-center gap-1 text-sm font-semibold">
                See books <span className="transition group-hover:translate-x-1">→</span>
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section aria-labelledby="skills" className="mt-20 grid gap-12 md:grid-cols-[1fr_2fr]">
        <div>
          <h2 id="skills" className="font-display text-2xl font-semibold">What coloring practises</h2>
          <p className="mt-3 leading-relaxed text-muted">Coloring looks simple, but it quietly builds skills children use every day.</p>
          <Link href="/blog/how-coloring-helps-kids-grow" className="mt-5 inline-flex items-center gap-1 text-sm font-semibold">
            Read: how coloring helps kids grow <span aria-hidden="true">→</span>
          </Link>
        </div>
        <div className="grid gap-8 sm:grid-cols-2">
          {SKILLS.map((s) => (
            <div key={s.t}>
              <div className={`h-1 w-10 rounded-lg ${s.bar}`} />
              <h3 className="mt-4 font-bold">{s.t}</h3>
              <p className="mt-1 text-sm leading-relaxed text-muted">{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      <section aria-labelledby="classroom" className="mt-20 grid gap-6 md:grid-cols-2">
        <div className="rounded-lg bg-white p-8 ring-1 ring-line">
          <h2 id="classroom" className="font-display text-2xl font-semibold">In the classroom</h2>
          <ul className="mt-5 space-y-3 text-sm leading-relaxed">
            <li className="flex gap-3"><span className="text-coral-600" aria-hidden="true">✓</span> Printables may be used in <strong>one classroom</strong>: print as many copies as your class needs.</li>
            <li className="flex gap-3"><span className="text-coral-600" aria-hidden="true">✓</span> Every printable comes in US Letter and A4.</li>
            <li className="flex gap-3"><span className="text-coral-600" aria-hidden="true">✓</span> Answer keys are included for mazes and puzzles.</li>
            <li className="flex gap-3"><span className="text-coral-600" aria-hidden="true">✓</span> Please don&apos;t share the files; point colleagues to our shop instead.</li>
          </ul>
          <Link href="/license" className="mt-6 inline-flex items-center gap-1 text-sm font-semibold">
            Read the printable license <span aria-hidden="true">→</span>
          </Link>
        </div>
        <div className="rounded-lg bg-coral-50 p-8">
          <h2 className="font-display text-2xl font-semibold">Try before you buy</h2>
          <p className="mt-3 leading-relaxed text-muted">
            Get our free printable pack: a few coloring pages plus a maze, a dot-to-dot and tracing. It&apos;s an easy way to see if our style suits your
            kids or class.
          </p>
          <ButtonLink href="/free-printables" variant="primary" size="sm" className="mt-6">
            Get free pages
          </ButtonLink>
        </div>
      </section>
    </div>
  );
}
