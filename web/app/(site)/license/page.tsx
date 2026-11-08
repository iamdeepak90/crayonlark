import Link from "next/link";
import { TextPage } from "@/components/site/TextPage";
import { pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "Printable license",
  description: "How you may use Crayonlark printables: personal and single-classroom use. No resale or sharing of the files.",
  path: "/license",
});

export default function LicensePage() {
  return (
    <TextPage
      title="Printable license"
      intro="Print as many copies as you need for your family or your class. Just don't resell or share the files."
      template
    >
      <p>
        This license covers every printable PDF from Crayonlark, both the free packs from this website and printables
        bought on Etsy.
      </p>

      <h2>You may</h2>
      <ul>
        <li>Print as many copies as you like for yourself and your own family.</li>
        <li>
          Print copies for the children in <strong>one</strong> classroom, homeschool group, therapy group or similar.
        </li>
        <li>Share photos of pages your kids have colored. We&apos;d love to see them!</li>
      </ul>

      <h2>You may not</h2>
      <ul>
        <li>Sell the files or printed copies, on their own or as part of anything else.</li>
        <li>Share, email, upload or post the PDF files, for example on a school website or a file-sharing site.</li>
        <li>Claim the designs as your own, or edit them and pass them off as new products.</li>
      </ul>

      <h2>Teachers and schools</h2>
      <p>
        Each copy of a printable covers one classroom. If other teachers would like to use it, please point them to our
        website or Etsy shop so they can get their own copy. For larger school licenses, just{" "}
        <Link href="/contact">ask us</Link>.
      </p>

      <h2>Paperbacks</h2>
      <p>Pages in our paperback books are for the owner of the book to color. Please don&apos;t copy them for others.</p>

      <h2>How the designs are made</h2>
      <p>
        Our designs are made with help from AI tools, then checked and edited by Crayonlark. They remain the property of
        Crayonlark.
      </p>
    </TextPage>
  );
}
