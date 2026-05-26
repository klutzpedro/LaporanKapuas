import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, Card, Empty } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";
import { toast } from "sonner";
import { FilePdf, DownloadSimple, Trash, Funnel } from "@phosphor-icons/react";

const INP = "bg-zinc-950 border-zinc-800 rounded-sm mt-1.5 h-9";

export default function HistoryPage() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [loading, setLoading] = useState(true);

  async function load(filters = {}) {
    setLoading(true);
    try {
      const params = {};
      if (filters.start_date) params.start_date = filters.start_date;
      if (filters.end_date) params.end_date = filters.end_date;
      const { data } = await api.get("/reports/history", { params });
      setItems(data);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Gagal memuat arsip.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  async function download(it) {
    try {
      const res = await api.get(`/reports/${it.id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url; a.download = it.filename || `BAIS_Summary_${it.report_date}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error("Gagal mengunduh.");
    }
  }

  async function del(id) {
    if (!confirm("Hapus arsip ini?")) return;
    try {
      await api.delete(`/reports/${id}`);
      toast.success("Arsip dihapus.");
      load({ start_date: start, end_date: end });
    } catch (e) {
      toast.error(e.response?.data?.detail || "Gagal menghapus.");
    }
  }

  function fmtSize(b) {
    if (!b) return "-";
    if (b < 1024) return `${b} B`;
    if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
    return `${(b / 1024 / 1024).toFixed(2)} MB`;
  }

  function fmtDate(iso) {
    if (!iso) return "-";
    const d = new Date(iso);
    return d.toLocaleString("id-ID", { hour12: false });
  }

  return (
    <div data-testid="history-page">
      <PageHeader
        overline="ARSIP // RIWAYAT LAPORAN"
        title="History Laporan PDF"
        subtitle="Semua laporan yang pernah di-generate disimpan di sini. Filter berdasarkan tanggal & unduh."
        testid="history-header"
      />

      <div className="p-6 space-y-6">
        <Card title="Filter Tanggal" color="#F59E0B" testid="history-filter-card">
          <form
            onSubmit={(e) => { e.preventDefault(); load({ start_date: start, end_date: end }); }}
            className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end"
            data-testid="history-filter-form"
          >
            <div>
              <Label className="overline">Dari Tanggal</Label>
              <Input
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                className={INP}
                data-testid="history-start-input"
              />
            </div>
            <div>
              <Label className="overline">Sampai Tanggal</Label>
              <Input
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                className={INP}
                data-testid="history-end-input"
              />
            </div>
            <Button
              type="submit"
              data-testid="history-apply-filter"
              className="bg-amber-500 hover:bg-amber-400 text-zinc-950 btn-tactical rounded-sm h-9"
            >
              <Funnel size={14} weight="bold" className="mr-2" />
              Terapkan Filter
            </Button>
            <Button
              type="button"
              onClick={() => { setStart(""); setEnd(""); load(); }}
              data-testid="history-reset-filter"
              className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 btn-tactical rounded-sm h-9"
            >
              Reset
            </Button>
          </form>
        </Card>

        <Card title="Daftar Laporan Tersimpan" kicker={`${items.length} arsip`} testid="history-list-card">
          {loading ? (
            <div className="text-xs text-zinc-500 py-8 text-center font-mono">Memuat arsip...</div>
          ) : items.length === 0 ? (
            <Empty text="Belum ada laporan tersimpan untuk filter ini." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="overline text-left border-b border-zinc-800">
                    <th className="pb-2 pt-1 pr-3">Tanggal Laporan</th>
                    <th className="pb-2 pt-1 pr-3">Generated</th>
                    <th className="pb-2 pt-1 pr-3">Oleh</th>
                    <th className="pb-2 pt-1 pr-3">Counts (L/K/G/M/Ge/P)</th>
                    <th className="pb-2 pt-1 pr-3">AI</th>
                    <th className="pb-2 pt-1 pr-3">Ukuran</th>
                    <th className="pb-2 pt-1 text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it) => (
                    <tr key={it.id} className="border-b border-zinc-800/60 hover:bg-zinc-900/40" data-testid={`history-row-${it.id}`}>
                      <td className="py-3 pr-3 font-mono text-amber-400 font-bold">{it.report_date}</td>
                      <td className="py-3 pr-3 font-mono text-zinc-400">{fmtDate(it.generated_at)}</td>
                      <td className="py-3 pr-3">{it.generated_by_name || "-"}</td>
                      <td className="py-3 pr-3 font-mono text-zinc-300">
                        {it.counts ? `${it.counts.lid}/${it.counts.kontra}/${it.counts.gal}/${it.counts.medmon}/${it.counts.geoint}/${it.counts.piket}` : "-"}
                      </td>
                      <td className="py-3 pr-3">
                        {it.has_ai_summary
                          ? <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm bg-emerald-500/15 text-emerald-400">YA</span>
                          : <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm bg-zinc-800 text-zinc-500">TDK</span>}
                      </td>
                      <td className="py-3 pr-3 font-mono text-zinc-400">{fmtSize(it.size_bytes)}</td>
                      <td className="py-3 text-right space-x-2 whitespace-nowrap">
                        <button
                          onClick={() => download(it)}
                          data-testid={`history-download-${it.id}`}
                          className="inline-flex items-center gap-1 px-2.5 h-7 bg-amber-500 hover:bg-amber-400 text-zinc-950 rounded-sm btn-tactical text-[10px]"
                        >
                          <DownloadSimple size={12} weight="bold" /> Unduh
                        </button>
                        {user?.role === "admin" && (
                          <button
                            onClick={() => del(it.id)}
                            data-testid={`history-delete-${it.id}`}
                            className="inline-flex items-center gap-1 px-2.5 h-7 bg-zinc-900 hover:bg-red-900 border border-zinc-800 text-zinc-400 hover:text-red-300 rounded-sm text-[10px]"
                          >
                            <Trash size={12} weight="bold" />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
