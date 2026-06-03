import { useEffect, useState } from "react";
import { api, apiErrorMsg } from "@/lib/api";
import { PageHeader, Card, Empty } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";
import { toast } from "sonner";
import { DownloadSimple, Trash, Funnel, Eye, X, Check } from "@phosphor-icons/react";

const INP = "bg-zinc-950 border-zinc-800 rounded-sm mt-1.5 h-9";

export default function HistoryPage() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [loading, setLoading] = useState(true);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewMeta, setPreviewMeta] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  async function load(filters = {}) {
    setLoading(true);
    try {
      const params = {};
      if (filters.start_date) params.start_date = filters.start_date;
      if (filters.end_date) params.end_date = filters.end_date;
      const { data } = await api.get("/reports/history", { params });
      setItems(data);
    } catch (e) {
      toast.error(apiErrorMsg(e, "Gagal memuat arsip."));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  // Auto-refresh every 60s so live monitoring rows update without manual reload
  useEffect(() => {
    const id = setInterval(() => {
      load({ start_date: start, end_date: end });
    }, 60000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [start, end]);

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

  async function preview(it) {
    setPreviewLoading(true);
    setPreviewMeta(it);
    try {
      const res = await api.get(`/reports/${it.id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      setPreviewUrl(url);
    } catch (e) {
      toast.error("Gagal memuat pratinjau.");
      setPreviewMeta(null);
    } finally {
      setPreviewLoading(false);
    }
  }

  function closePreview() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setPreviewMeta(null);
  }

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  async function del(id) {
    if (!confirm("Hapus arsip ini?")) return;
    try {
      await api.delete(`/reports/${id}`);
      toast.success("Arsip dihapus.");
      load({ start_date: start, end_date: end });
    } catch (e) {
      toast.error(apiErrorMsg(e, "Gagal menghapus."));
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
            <div className="relative">
              <div
                className="overflow-y-auto overflow-x-auto pr-1 history-scroll"
                style={{ maxHeight: items.length > 7 ? "440px" : "auto" }}
                data-testid="history-scroll-container"
              >
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-zinc-950 z-10">
                    <tr className="overline text-left border-b border-zinc-800">
                      <th className="pb-2 pt-1 pr-3">Tanggal Laporan</th>
                      <th className="pb-2 pt-1 pr-3">Generated</th>
                      <th className="pb-2 pt-1 pr-3">Absensi Tim</th>
                      <th className="pb-2 pt-1 pr-3">AI</th>
                      <th className="pb-2 pt-1 pr-3">Ukuran</th>
                      <th className="pb-2 pt-1 text-right">Aksi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((it) => (
                      <tr key={it.id} className={`border-b border-zinc-800/60 hover:bg-zinc-900/40 ${it.is_live ? "bg-amber-500/5" : ""}`} data-testid={`history-row-${it.id}`}>
                        <td className="py-3 pr-3 font-mono text-amber-400 font-bold">
                          <div className="flex items-center gap-2">
                            {it.report_date}
                            {it.is_live && (
                              <span
                                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-sm bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[9px] uppercase tracking-wider"
                                data-testid="live-badge"
                                title="Monitoring real-time — PDF belum di-generate"
                              >
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                                LIVE
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 pr-3 font-mono text-zinc-400">
                          {it.is_live ? <span className="text-amber-500/70 text-[10px]">— monitoring —</span> : fmtDate(it.generated_at)}
                        </td>
                        <td className="py-3 pr-3"><AttendanceBadges attendance={it.attendance || {}} /></td>
                        <td className="py-3 pr-3">
                          {it.has_ai_summary
                            ? <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm bg-emerald-500/15 text-emerald-400">YA</span>
                            : <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm bg-zinc-800 text-zinc-500">TDK</span>}
                        </td>
                        <td className="py-3 pr-3 font-mono text-zinc-400">{it.is_live ? "-" : fmtSize(it.size_bytes)}</td>
                        <td className="py-3 text-right space-x-1 whitespace-nowrap">
                          {it.is_live ? (
                            <span className="text-[10px] font-mono text-zinc-500 italic" data-testid={`history-live-hint-${it.report_date}`}>
                              PDF belum di-generate
                            </span>
                          ) : (
                            <>
                              <button
                                onClick={() => preview(it)}
                                data-testid={`history-preview-${it.id}`}
                                className="inline-flex items-center gap-1 px-2.5 h-7 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 hover:border-amber-500/70 text-zinc-200 hover:text-amber-400 rounded-sm btn-tactical text-[10px]"
                              >
                                <Eye size={12} weight="bold" /> Preview
                              </button>
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
                            </>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {items.length > 7 && (
                <div className="mt-2 flex items-center justify-between text-[10px] font-mono uppercase tracking-wider text-zinc-500">
                  <span data-testid="history-scroll-hint">
                    Menampilkan 7 terbaru — geser ke bawah untuk arsip lama (total {items.length} arsip)
                  </span>
                  <span className="text-amber-500/70">↓ scroll</span>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* PDF Preview Modal */}
      {(previewMeta || previewLoading) && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={closePreview}
          data-testid="preview-modal"
        >
          <div
            className="bg-zinc-950 border border-zinc-800 rounded-sm w-full max-w-5xl h-[90vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between gap-4 px-4 py-3 border-b border-zinc-800 bg-zinc-900">
              <div>
                <p className="overline">PRATINJAU PDF</p>
                <h3 className="text-sm font-bold uppercase tracking-wide mt-0.5">
                  BAIS Summary {previewMeta?.report_date || ""}
                </h3>
              </div>
              <div className="flex items-center gap-2">
                {previewMeta && !previewLoading && (
                  <button
                    onClick={() => download(previewMeta)}
                    data-testid="preview-download-button"
                    className="inline-flex items-center gap-1.5 px-3 h-8 bg-amber-500 hover:bg-amber-400 text-zinc-950 rounded-sm btn-tactical text-[11px]"
                  >
                    <DownloadSimple size={12} weight="bold" /> Unduh
                  </button>
                )}
                <button
                  onClick={closePreview}
                  data-testid="preview-close-button"
                  className="inline-flex items-center justify-center w-8 h-8 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-red-400 rounded-sm"
                  aria-label="Tutup pratinjau"
                >
                  <X size={14} weight="bold" />
                </button>
              </div>
            </div>
            <div className="flex-1 bg-zinc-900">
              {previewLoading ? (
                <div className="h-full flex items-center justify-center text-xs font-mono text-zinc-500">
                  Memuat pratinjau PDF...
                </div>
              ) : previewUrl ? (
                <object
                  data={previewUrl}
                  type="application/pdf"
                  className="w-full h-full"
                  data-testid="preview-iframe"
                >
                  <div className="h-full flex items-center justify-center text-sm text-zinc-400 p-6 text-center">
                    Browser Anda tidak mendukung pratinjau PDF inline.
                    <br />
                    <button
                      onClick={() => download(previewMeta)}
                      className="mt-3 inline-flex items-center gap-1.5 px-3 h-9 bg-amber-500 hover:bg-amber-400 text-zinc-950 rounded-sm btn-tactical text-[11px]"
                    >
                      <DownloadSimple size={14} weight="bold" /> Unduh PDF
                    </button>
                  </div>
                </object>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const TEAM_LABELS = [
  { key: "lid", short: "LID" },
  { key: "kontra", short: "KTR" },
  { key: "gal", short: "GAL" },
  { key: "medmon", short: "MED" },
  { key: "geoint", short: "GEO" },
  { key: "piket", short: "PKT" },
];

function AttendanceBadges({ attendance }) {
  const submitted = TEAM_LABELS.filter((t) => (attendance[t.key] || 0) > 0).length;
  return (
    <div className="flex items-center gap-1.5" data-testid="attendance-badges">
      <span className="text-[10px] font-mono text-zinc-500 tabular-nums">{submitted}/6</span>
      {TEAM_LABELS.map((t) => {
        const count = attendance[t.key] || 0;
        const ok = count > 0;
        return (
          <span
            key={t.key}
            title={ok ? `${t.short}: ${count} laporan` : `${t.short}: belum input`}
            data-testid={`attendance-${t.key}-${ok ? "ok" : "miss"}`}
            className={`inline-flex items-center gap-0.5 px-1.5 h-5 rounded-sm font-mono text-[9px] font-bold tracking-wider border ${
              ok
                ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/40"
                : "bg-zinc-900 text-zinc-600 border-zinc-800 line-through decoration-zinc-700"
            }`}
          >
            {ok ? <Check size={8} weight="bold" /> : null}
            {t.short}
          </span>
        );
      })}
    </div>
  );
}
