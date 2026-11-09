import { Check } from "lucide-react";
import type { PaidApis } from "@/lib/types";
import { Card } from "./ui";

const inr = (n: number) => `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

/** Every paid API: key set or missing (keys are entered under Integrations), who uses it, spend this month. */
export default function PaidApisCard({ data }: { data: PaidApis }) {
  return (
    <Card title="Paid APIs" className="lg:col-span-2">
      <p className="mb-3 text-sm text-slate-600">
        All optional. Enter keys under <em>Integrations</em> above (AI providers, Web search); they are never shown again. Choose which agent uses which provider in <em>AI providers &amp; models</em> below. Every call counts against the monthly budget.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200">
            <tr>
              <th className="px-2 py-1 text-left font-semibold">Service</th>
              <th className="px-2 py-1 text-left font-semibold">Key</th>
              <th className="px-2 py-1 text-left font-semibold">Used by now</th>
              <th className="px-2 py-1 text-left font-semibold whitespace-nowrap">{data.month}</th>
            </tr>
          </thead>
          <tbody>
            {data.apis.map((a) => (
              <tr key={a.id} className="border-b border-slate-100 align-top">
                <td className="px-2 py-2">
                  <div className="font-semibold">{a.name}</div>
                  <div className="text-xs text-slate-600">{a.used_for}</div>
                  <div className="mt-1 text-xs text-slate-500">
                    {a.url}
                  </div>
                </td>
                <td className="px-2 py-2 whitespace-nowrap">
                  {a.key_set ? <span className="inline-flex items-center gap-1 font-medium text-emerald-700 dark:text-emerald-400"><Check className="size-3.5" aria-hidden="true" /> set</span> : <span className="text-slate-500">missing</span>}
                </td>
                <td className="px-2 py-2">{a.used_by.length ? a.used_by.join(", ") : <span className="text-slate-500">—</span>}</td>
                <td className="px-2 py-2 whitespace-nowrap">{inr(a.month_inr)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
