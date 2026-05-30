import { Info } from "@phosphor-icons/react";

/**
 * Shown when the loaded items belong to a period older than the current expected period.
 * Determines this by comparing items[0].report_date vs currentDate.
 */
export function PreviousPeriodBanner({ items, currentDate }) {
  if (!items || items.length === 0) return null;
  const itemDate = items[0]?.report_date;
  if (!itemDate || !currentDate || itemDate === currentDate) return null;

  // Format old date
  const fmt = (d) => {
    try {
      return new Date(d + "T00:00:00").toLocaleDateString("id-ID", {
        day: "2-digit", month: "short", year: "numeric",
      });
    } catch { return d; }
  };

  return (
    <div
      className="border-l-2 border-amber-500 bg-amber-500/10 px-3 py-2 mb-3 flex items-start gap-2 rounded-sm"
      data-testid="previous-period-banner"
    >
      <Info size={14} weight="bold" className="text-amber-400 mt-0.5 shrink-0" />
      <div className="text-xs text-amber-100/90">
        <p className="font-bold uppercase tracking-wider text-[10px] text-amber-400">Belum ada laporan periode ini</p>
        <p className="text-zinc-300 leading-snug">
          Menampilkan data terakhir dari periode <span className="font-mono font-bold text-amber-300">{fmt(itemDate)}</span>.
          Silakan input laporan baru bila ada update.
        </p>
      </div>
    </div>
  );
}
