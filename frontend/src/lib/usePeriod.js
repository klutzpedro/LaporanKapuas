import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/** Compute the current reporting window aligned to 12:00 WIB cycle:
 *  - Before 12:00 WIB → window is YESTERDAY 12:00 → TODAY 12:00 (report_date = yesterday)
 *  - After 12:00 WIB → window is TODAY 12:00 → TOMORROW 12:00 (report_date = today)
 */
export function usePeriod() {
  const [info, setInfo] = useState(null);
  useEffect(() => {
    api.get("/daily/info").then((r) => setInfo(r.data)).catch(() => setInfo(null));
  }, []);

  const reportDate = info?.report_date || "";
  const beforeNoon = !!info?.before_noon;

  // Period label
  function periodLabel() {
    if (!reportDate) return "—";
    const start = new Date(reportDate + "T00:00:00");
    const end = new Date(start);
    end.setDate(end.getDate() + 1);
    const fmt = (d) =>
      d.toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" }).toUpperCase();
    return `${fmt(start)} 12:00 — ${fmt(end)} 12:00 WIB`;
  }

  return { info, reportDate, beforeNoon, periodLabel: periodLabel() };
}
