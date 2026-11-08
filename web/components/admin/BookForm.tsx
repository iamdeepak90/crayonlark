"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { Button, Card } from "./ui";

type Niche = { id: number; name: string; theme: string; age_range: string };

export default function BookForm({ niches, defaultNiche }: { niches: Niche[]; defaultNiche?: number }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(form: FormData) {
    setBusy(true);
    setError("");
    const words = String(form.get("words") ?? "")
      .split(/[,\n]/)
      .map((w) => w.trim())
      .filter(Boolean);
    const [ageMin, ageMax] = String(form.get("ages") ?? "4-8").split("-").map(Number);
    try {
      const book = await api<{ id: number }>("/api/admin/books", {
        body: {
          title: form.get("title"),
          subtitle: form.get("subtitle"),
          series: form.get("series"),
          volume: Number(form.get("volume") || 1),
          niche_id: form.get("niche_id") ? Number(form.get("niche_id")) : null,
          trim: form.get("trim"),
          format: "paperback",
          age_min: ageMin || 4,
          age_max: ageMax || 8,
          themes: String(form.get("themes") ?? "").split(",").map((t) => t.trim()).filter(Boolean),
          ai_interior_images: form.get("ai_interior_images") === "on",
          ai_cover_image: form.get("ai_cover_image") === "on",
          ai_text: form.get("ai_text") === "on",
          ai_tools: form.get("ai_tools"),
          activity_plan: {
            mazes: Number(form.get("mazes") || 0),
            wordsearch_words: words,
            dot2dot: form.getAll("dot2dot"),
            tracing: String(form.get("tracing") ?? "").toUpperCase(),
            numbers_upto: Number(form.get("numbers_upto") || 0),
            sudoku: Number(form.get("sudoku") || 0) ? [4] : [],
          },
        },
      });
      router.push(`/books/${book.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed");
      setBusy(false);
    }
  }

  const input = "mt-1 w-full rounded-lg border border-slate-300 px-3 py-2";
  return (
    <form action={submit} className="grid max-w-3xl gap-4">
      <Card title="Book">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm font-semibold sm:col-span-2">
            Title
            <input name="title" required minLength={3} className={input} placeholder="Dinosaur Coloring Book for Kids Ages 4-8" />
          </label>
          <label className="text-sm font-semibold sm:col-span-2">
            Subtitle
            <input name="subtitle" className={input} placeholder="50 Cute Dinosaurs to Color, Mazes and Puzzles" />
          </label>
          <label className="text-sm font-semibold">
            Series
            <input name="series" className={input} />
          </label>
          <label className="text-sm font-semibold">
            Volume
            <input name="volume" type="number" min={1} defaultValue={1} className={input} />
          </label>
          <label className="text-sm font-semibold">
            Niche
            <select name="niche_id" defaultValue={defaultNiche ?? ""} className={input}>
              <option value="">(none)</option>
              {niches.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.name} ({n.age_range})
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm font-semibold">
            Trim
            <select name="trim" className={input} defaultValue="8.5x11">
              <option value="8.5x11">8.5 × 11 in</option>
              <option value="8.5x8.5">8.5 × 8.5 in</option>
            </select>
          </label>
          <label className="text-sm font-semibold">
            Ages
            <input name="ages" defaultValue="4-8" pattern="\d{1,2}-\d{1,2}" className={input} />
          </label>
          <label className="text-sm font-semibold">
            Themes (comma separated)
            <input name="themes" className={input} placeholder="dinosaurs, animals" />
          </label>
        </div>
      </Card>
      <Card title="AI disclosure (required by KDP and Etsy)">
        <div className="grid gap-2 text-sm">
          <label className="flex items-center gap-2">
            <input type="checkbox" name="ai_interior_images" defaultChecked /> Interior images are AI-generated
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" name="ai_cover_image" /> Cover image is AI-generated
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" name="ai_text" defaultChecked /> Text (title/description) is AI-generated
          </label>
          <label className="font-semibold">
            AI tools used
            <input name="ai_tools" className={input} placeholder="ChatGPT image generation, Claude" />
          </label>
        </div>
      </Card>
      <Card title="Activities (no AI)">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm font-semibold">
            Mazes
            <input name="mazes" type="number" min={0} max={10} defaultValue={2} className={input} />
          </label>
          <label className="text-sm font-semibold">
            Tracing letters (e.g. ABC)
            <input name="tracing" className={input} />
          </label>
          <label className="text-sm font-semibold sm:col-span-2">
            Word search words (comma separated, leave empty for none)
            <input name="words" className={input} placeholder="DINO, EGG, ROAR, TAIL" />
          </label>
          <label className="text-sm font-semibold">
            Number tracing up to
            <input name="numbers_upto" type="number" min={0} max={10} defaultValue={0} className={input} />
          </label>
          <fieldset className="text-sm">
            <legend className="font-semibold">Dot-to-dot</legend>
            {["star", "heart", "fish", "house", "kite"].map((s) => (
              <label key={s} className="mr-3 inline-flex items-center gap-1">
                <input type="checkbox" name="dot2dot" value={s} defaultChecked={s === "star"} /> {s}
              </label>
            ))}
          </fieldset>
          <label className="flex items-center gap-2 text-sm font-semibold">
            <input type="checkbox" name="sudoku" value="1" defaultChecked /> 4×4 number puzzle
          </label>
        </div>
      </Card>
      {error && <p role="alert" className="text-rose-700">{error}</p>}
      <div>
        <Button disabled={busy}>{busy ? "Creating…" : "Create book"}</Button>
      </div>
    </form>
  );
}
