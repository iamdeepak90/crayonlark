/** Static website copy shared by several pages (FAQ, themes, age groups). */

export type Faq = { q: string; a: string };

export const FAQ: Faq[] = [
  {
    q: "Where can I buy Crayonlark books?",
    a: "Paperbacks are sold on Amazon. Printable PDF versions are available in our Etsy shop. Each book page on this site links to both when they are available.",
  },
  {
    q: "Will markers bleed through the pages?",
    a: "Each design is printed on one side only, with a blank page behind it, so the next picture stays clean even if a marker bleeds through.",
  },
  {
    q: "What ages are the books for?",
    a: "Every book shows an age range. Books for toddlers have big, bold shapes; books for older kids have more detail, mazes and puzzles.",
  },
  {
    q: "Can I use the printables in my classroom?",
    a: "Yes. Printables may be used at home or in a single classroom. Please don't share or resell the files. See our printable license for details.",
  },
  {
    q: "Which paper sizes do the printables come in?",
    a: "Every printable includes a US Letter and an A4 version, so it prints correctly wherever you are.",
  },
  {
    q: "How are the illustrations made?",
    a: "Some illustrations are created with the help of AI tools. We then clean them up, check every page by hand for clear lines and kid-friendly content, and arrange them into books. Each listing says when AI tools were used.",
  },
  {
    q: "Do you use famous characters?",
    a: "No. All our designs are original: no cartoon characters, brands or logos.",
  },
  {
    q: "How do I get the free coloring pages?",
    a: "Enter your email on the free printables page. We send one email to confirm, and then you get the download link straight away.",
  },
  {
    q: "How do I contact you?",
    a: "Use the contact form. We usually reply within a couple of working days. For paperback orders, shipping and returns, please contact Amazon.",
  },
];

export type Theme = { slug: string; name: string; blurb: string; emoji: string };

/** The themes we make books about. A theme links to the catalogue once it has a live book. */
export const THEMES: Theme[] = [
  { slug: "farm-animals", name: "Farm animals", blurb: "Cows, pigs, ducks and a big red barn.", emoji: "🐮" },
  { slug: "ocean", name: "Ocean", blurb: "Friendly fish, whales and coral reefs.", emoji: "🐠" },
  { slug: "dinosaurs", name: "Dinosaurs", blurb: "Cute, not scary, dinosaurs.", emoji: "🦕" },
  { slug: "space", name: "Space", blurb: "Rockets, planets and astronauts.", emoji: "🚀" },
  { slug: "vehicles", name: "Trucks & trains", blurb: "Diggers, fire trucks and trains.", emoji: "🚂" },
  { slug: "bugs", name: "Bugs & gardens", blurb: "Ladybugs, bees and butterflies.", emoji: "🐞" },
  { slug: "jungle", name: "Jungle safari", blurb: "Lions, elephants and parrots.", emoji: "🦁" },
  { slug: "alphabet", name: "ABC & tracing", blurb: "Letters to trace and colour.", emoji: "🔤" },
  { slug: "numbers", name: "Numbers & counting", blurb: "Count, connect the dots, colour.", emoji: "🔢" },
  { slug: "seasons", name: "Seasons", blurb: "Snow days, spring flowers, summer fun.", emoji: "🍂" },
  { slug: "toddler-shapes", name: "First shapes", blurb: "Very big, simple shapes for little hands.", emoji: "🟡" },
  { slug: "kind-monsters", name: "Kind monsters", blurb: "Silly monsters doing everyday things.", emoji: "👾" },
];


export const AGE_GROUPS = [
  { age: 3, label: "Ages 2–4", title: "Toddlers", text: "Big shapes, first words and simple tracing.", bg: "bg-sun-50", eyebrow: "text-coral-600" },
  { age: 6, label: "Ages 4–8", title: "Little artists", text: "Cute scenes, mazes, dot-to-dot and ABCs.", bg: "bg-sun-50", eyebrow: "text-coral-600" },
  { age: 9, label: "Ages 8–12", title: "Big kids", text: "Detailed designs, word searches and puzzles.", bg: "bg-sun-50", eyebrow: "text-coral-600" },
];
