import Link from "next/link";
import { TextPage } from "@/components/site/TextPage";
import { pageMetadata } from "@/lib/public";

export const metadata = pageMetadata({
  title: "Terms of use",
  description: "The simple rules for using the Crayonlark website and free printables.",
  path: "/terms",
});

export default function TermsPage() {
  return (
    <TextPage title="Terms of use" intro="The simple rules for using this website." template>
      <h2>Using this website</h2>
      <p>
        You&apos;re welcome to browse, read the blog and download our free printables for your own use. Please don&apos;t
        try to break, overload or misuse the website or its forms.
      </p>

      <h2>Buying books</h2>
      <p>
        We don&apos;t sell anything directly on this website. Paperbacks are sold by Amazon and printable PDFs through our
        Etsy shop. Prices, payment, delivery and refunds are handled by those sites under their own terms.
      </p>

      <h2>Our designs</h2>
      <p>
        All books, pages, pictures and text on this website belong to Crayonlark. Our artwork is made with the help of AI
        tools and then checked and edited by us. How you may use printables is explained in the{" "}
        <Link href="/license">printable license</Link>.
      </p>

      <h2>Accuracy</h2>
      <p>
        We work hard to make every page friendly, age-appropriate and correct. If you spot a mistake, please{" "}
        <Link href="/contact">tell us</Link> and we&apos;ll fix it. Coloring and activity pages are meant to be used with
        an adult nearby. Please choose crayons, scissors and other supplies that are right for your child&apos;s age.
      </p>

      <h2>Links to other websites</h2>
      <p>We link to Amazon, Etsy and sometimes other sites. We aren&apos;t responsible for their content.</p>

      <h2>Liability</h2>
      <p>
        This website and the free printables are provided as they are. As far as the law allows, Crayonlark is not
        liable for any loss caused by using them.
      </p>

      <h2>Changes</h2>
      <p>We may update these terms from time to time. The latest version is always on this page.</p>
    </TextPage>
  );
}
