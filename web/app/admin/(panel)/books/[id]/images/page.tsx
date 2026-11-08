import ImageGrid from "@/components/admin/ImageGrid";
import { PageTitle } from "@/components/admin/ui";
import { serverApi } from "@/lib/api";
import type { BookDetail } from "@/lib/types";

// Scene prompts without a picture yet (see the book page) are not shown in the grid.
const NO_FILE = new Set(["pending", "generating", "failed"]);

export default async function ImagesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const b = await serverApi<BookDetail>(`/api/admin/books/${id}`);
  const settings = await serverApi<{ images_per_book: { min: number; max: number } }>("/api/admin/settings");
  return (
    <>
      <PageTitle>Images · {b.title}</PageTitle>
      <ImageGrid bookId={b.id} status={b.status} initial={b.images.filter((i) => !NO_FILE.has(i.status))} limits={settings.images_per_book} />
    </>
  );
}
