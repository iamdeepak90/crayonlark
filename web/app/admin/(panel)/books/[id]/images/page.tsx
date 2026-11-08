import ImageGrid from "@/components/admin/ImageGrid";
import { PageTitle } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { BookDetail } from "@/lib/types";

export default async function ImagesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const b = await serverApi<BookDetail>(`/api/admin/books/${id}`);
  const settings = await serverApi<{ images_per_book: { min: number; max: number } }>("/api/admin/settings");
  return (
    <>
      <PageTitle>Images · {b.title}</PageTitle>
      <ImageGrid bookId={b.id} status={b.status} initial={b.images} limits={settings.images_per_book} />
    </>
  );
}
