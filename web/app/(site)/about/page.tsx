import Link from "next/link";
import { TextPage } from "@/components/site/TextPage";
import { pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "About Crayonlark",
  description: "Who makes Crayonlark books, and how: designed with help from AI tools, with every page checked and edited by a person.",
  path: "/about",
});

export default function AboutPage() {
  return (
    <TextPage title="About Crayonlark" intro="A tiny studio making friendly coloring and activity books for kids.">
      <p>
        Crayonlark is a one-person studio. We make coloring and activity books for children, for parents who want a
        calm activity at home and for teachers who need something simple for the classroom.
      </p>

      <h2>How our books are made</h2>
      <p>
        We want to be open about this: our books are designed with help from AI tools. We use them to sketch ideas and
        create the first version of the artwork. Then a person looks at every single page, edits it, and throws out
        anything that isn&apos;t clear, friendly and right for little kids.
      </p>
      <p>
        Each book page on this site says which parts were made with AI tools. Our books are not hand-drawn, and we
        won&apos;t pretend they are.
      </p>

      <h2>What we care about</h2>
      <ul>
        <li>Clear, bold outlines that are easy for small hands to color.</li>
        <li>Kind, age-appropriate pictures and simple, correct facts.</li>
        <li>Original designs only. No famous cartoon characters or brands.</li>
        <li>Honest descriptions, so you know exactly what you are getting.</li>
      </ul>

      <h2>Where to find our books</h2>
      <p>
        Paperbacks are sold on Amazon and printable PDFs on Etsy. You&apos;ll find the links on each{" "}
        <Link href="/books">book page</Link>. You can also start with a{" "}
        <Link href="/free-printables">free printable pack</Link>.
      </p>
      <p>
        Spotted a mistake, or have an idea for a book? We&apos;d love to hear from you on the{" "}
        <Link href="/contact">contact page</Link>.
      </p>
    </TextPage>
  );
}
