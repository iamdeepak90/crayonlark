import Image from "next/image";

export default function HomePage() {
  return (
    <main className="mx-auto flex max-w-3xl flex-col items-center gap-6 px-6 py-24 text-center">
      <Image src="/brand/lark.svg" alt="" width={120} height={120} priority />
      <h1 className="text-5xl font-bold tracking-tight">Crayonlark</h1>
      <p className="text-xl text-ink-soft">Little books for big imaginations</p>
    </main>
  );
}
