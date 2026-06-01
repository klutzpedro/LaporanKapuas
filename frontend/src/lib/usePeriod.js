import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/** Compute the current reporting window. The cutoff hour comes from /daily/info.
 *  - Before cutoff → window is YESTERDAY cutoff → TODAY cutoff (report_date = yesterday)
 *  - After cutoff → window is TODAY cutoff → TOMORROW cutoff (report_date = today)
 */
export function usePeriod() {
  const [info, setInfo] = useState(null);
  useEffect(() => {
    api.get("/daily/info").then((r) => setInfo(r.data)).catch(() => setInfo(null));
  }, []);

  const reportDate = info?.report_date || "";
  const beforeCutoff = !!(info?.before_cutoff ?? info?.before_noon);
  const hh = String(info?.cutoff_hour ?? 9).padStart(2, "0");
  const mm = String(info?.cutoff_minute ?? 0).padStart(2, "0");
  const cutoffLabel = `${hh}:${mm}`;

  function periodLabel() {
    if (!reportDate) return "—";
    const start = new Date(reportDate + "T00:00:00");
    const end = new Date(start);
    end.setDate(end.getDate() + 1);
    const fmt = (d) =>
      d.toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" }).toUpperCase();
    return `${fmt(start)} ${cutoffLabel} — ${fmt(end)} ${cutoffLabel} WIB`;
  }

  return {
    info,
    reportDate,
    beforeNoon: beforeCutoff, // legacy alias
    beforeCutoff,
    cutoffLabel,
    periodLabel: periodLabel(),
  };
}
