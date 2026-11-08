import { PageTitle } from "@/components/admin/ui";
import BookForm from "@/components/admin/BookForm";
import { serverApi } from "@/lib/api";

type Niche = { id: number; name: string; theme: string; age_range: string; status: string };

export default async function NewBookPage({ searchParams }: { searchParams: Promise<{ niche?: string }> }) {
  const { niche } = await searchParams;
  const niches = await serverApi<Niche[]>("/api/admin/niches?status=approved");
  return (
    <>
      <PageTitle>New book</PageTitle>
      <BookForm niches={niches} defaultNiche={niche ? Number(niche) : undefined} />
    </>
  );
}
