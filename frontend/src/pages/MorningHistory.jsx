import { useEffect, useState } from "react";
import { api, apiErrorMsg } from "@/lib/api";
import { PageHeader, Card, Empty } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { toast } from "sonner";
import { DownloadSimple, Trash, Eye, X, Sun, ArrowsClockwise, CircleNotch, PencilSimple, FloppyDisk, ChartBar } from "@phosphor-icons/react";
import RichEditor from "@/components/RichEditor";

function fmtDate(s) {
  if (!s) return "-";
  try { return new Date(s).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" }); }
  catch { return s; }
}
function fmtSize(n) {
  if (!n) return "-";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

export default function MorningHistory() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewMeta, setPreviewMeta] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  // Edit modal state
  const [editMeta, setEditMeta] = useState(null);
  const [editHtml, setEditHtml] = useState("");
  const [editText, setEditText] = useState("");
  const [editLoading, setEditLoading] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  // Infographic loading state (per-row id)
  const [infoLoadingId, setInfoLoadingId] = useState(null);

  async function load() {
    setLoading(true);
    try {
      const { data } = await api.get("/morning-reports/history");
      setItems(data);
    } catch (e) {
      toast.error(apiErrorMsg(e, "Gagal memuat laporan pagi."));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  // Auto-refresh tiap 60 detik
  useEffect(() => {
    const id = setInterval(load, 60000);
    return () => clearInterval(id);
  }, []);

  async function generateNow() {
    setGenerating(true);
    try {
      const today = new Date();
      const yyyy = today.getFullYear();
      const mm = String(today.getMonth() + 1).padStart(2, "0");
      const dd = String(today.getDate()).padStart(2, "0");
      const report_date = `${yyyy}-${mm}-${dd}`;
      await api.post(`/morning-reports/generate?report_date=${report_date}`, null, { responseType: "blob" });
      toast.success(`Laporan pagi ${report_date} berhasil di-generate.`);
      await load();
    } catch (e) {
      toast.error(apiErrorMsg(e, "Gagal generate laporan pagi."));
    } finally {
      setGenerating(false);
    }
  }

  async function download(it) {
    try {
      const res = await api.get(`/morning-reports/${it.id}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url; a.download = it.filename || `Laporan_Pagi_${it.report_date}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error("Gagal mengunduh.");
    }
  }

  async function downloadInfographic(it) {
    setInfoLoadingId(it.id);
    try {
      const res = await api.post(`/morning-reports/${it.id}/infographic`, null, {
        responseType: "blob",
        timeout: 180000, // 3 minutes — Claude SVG can take time
      });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `Infografis_Laporan_Pagi_${it.report_date}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast.success("Infografis berhasil di-generate.");
    } catch (e) {
      toast.error(apiErrorMsg(e, "Gagal generate infografis."));
    } finally {
      setInfoLoadingId(null);
    }
  }

  async function preview(it) {
    setPreviewMeta(it);
    setPreviewLoading(true);
    setPreviewUrl(null);
    try {
      const res = await api.get(`/morning-reports/${it.id}/download`, { responseType: "blob" });
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

  async function del(id) {
    if (!window.confirm("Hapus laporan pagi ini?")) return;
    try {
      await api.delete(`/morning-reports/${id}`);
      toast.success("Laporan pagi dihapus.");
      await load();
    } catch (e) {
      toast.error("Gagal menghapus.");
    }
  }

  async function openEdit(it) {
    setEditMeta(it);
    setEditLoading(true);
    setEditHtml("");
    setEditText("");
    try {
      const { data } = await api.get(`/morning-reports/${it.id}/content`);
      // Prefer HTML; fallback to plain text wrapped in <p>
      const html = data.ai_html || (data.ai_text
        ? data.ai_text.split("\n\n").map(p => `<p>${p.replace(/\n/g, "<br/>")}</p>`).join("")
        : "");
      setEditHtml(html);
      setEditText(data.ai_text || "");
    } catch (e) {
      toast.error(apiErrorMsg(e, "Gagal memuat konten."));
      setEditMeta(null);
    } finally {
      setEditLoading(false);
    }
  }

  function closeEdit() {
    setEditMeta(null);
    setEditHtml("");
    setEditText("");
  }

  async function saveEdit() {
    if (!editMeta) return;
    setEditSaving(true);
    try {
      // Derive plain text from HTML for AI parsing fallback
      const tmp = document.createElement("div");
      tmp.innerHTML = editHtml;
      const plainText = tmp.innerText || tmp.textContent || editText;
      await api.patch(`/morning-reports/${editMeta.id}/edit`, {
        ai_html: editHtml,
        ai_text: plainText,
      });
      toast.success("Laporan pagi diperbarui & PDF dirender ulang.");
      closeEdit();
      await load();
    } catch (e) {
      toast.error(apiErrorMsg(e, "Gagal menyimpan."));
    } finally {
      setEditSaving(false);
    }
  }

  return (
    <div className="space-y-6" data-testid="morning-history-page">
      <PageHeader
        title="LAPORAN PAGI GEOSPASIKA"
        subtitle="Auto-generated tiap pukul 07:00 WIB · dari data tim hari sebelumnya · Executive Summary + LID + KONTRA + GAL + MEDMON + GEOINT"
        right={
          <div className="flex items-center gap-2">
            <Button
              onClick={load}
              data-testid="morning-refresh"
              variant="outline"
              className="h-9 px-3 rounded-sm border-zinc-700 hover:border-amber-500/70 text-xs"
            >
              <ArrowsClockwise size={14} weight="bold" className="mr-1.5" /> Muat Ulang
            </Button>
            <Button
              onClick={generateNow}
              disabled={generating}
              data-testid="morning-generate-now"
              className="h-9 px-3 rounded-sm bg-amber-500 hover:bg-amber-400 text-zinc-950 font-bold text-xs"
            >
              {generating
                ? <><CircleNotch size={14} weight="bold" className="mr-1.5 animate-spin" />Memproses...</>
                : <><Sun size={14} weight="bold" className="mr-1.5" />Generate Sekarang</>}
            </Button>
          </div>
        }
      />

      <Card className="p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold tracking-wider uppercase text-zinc-300">Daftar Laporan Pagi</h3>
          <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
            Total: <b className="text-amber-400">{items.length}</b> · Auto-refresh 60s
          </span>
        </div>

        {loading ? (
          <Empty title="Memuat..." subtitle="Mengambil daftar laporan pagi" />
        ) : items.length === 0 ? (
          <Empty
            title="Belum ada laporan pagi"
            subtitle="Laporan pagi akan otomatis dibuat tiap jam 07:00 WIB. Anda juga bisa generate manual via tombol di atas."
            icon={Sun}
          />
        ) : (
          <div className="relative">
            <div
              className="overflow-y-auto overflow-x-auto pr-1 history-scroll"
              style={{ maxHeight: items.length > 7 ? "440px" : "auto" }}
              data-testid="morning-scroll-container"
            >
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-zinc-950 z-10">
                  <tr className="overline text-left border-b border-zinc-800">
                    <th className="pb-2 pt-1 pr-3">Periode</th>
                    <th className="pb-2 pt-1 pr-3">Sumber Data</th>
                    <th className="pb-2 pt-1 pr-3">Generated</th>
                    <th className="pb-2 pt-1 pr-3">AI</th>
                    <th className="pb-2 pt-1 pr-3">Ukuran</th>
                    <th className="pb-2 pt-1 text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it) => (
                    <tr key={it.id} className="border-b border-zinc-800/60 hover:bg-zinc-900/40" data-testid={`morning-row-${it.id}`}>
                      <td className="py-3 pr-3 font-mono text-amber-400 font-bold">{it.report_date}</td>
                      <td className="py-3 pr-3 font-mono text-zinc-400">{it.source_date || "-"}</td>
                      <td className="py-3 pr-3 font-mono text-zinc-400">{fmtDate(it.generated_at)}</td>
                      <td className="py-3 pr-3">
                        {it.has_ai_summary
                          ? <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm bg-emerald-500/15 text-emerald-400">YA</span>
                          : <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm bg-zinc-800 text-zinc-500">TDK</span>}
                      </td>
                      <td className="py-3 pr-3 font-mono text-zinc-400">{fmtSize(it.size_bytes)}</td>
                      <td className="py-3 text-right space-x-1 whitespace-nowrap">
                        <button
                          onClick={() => preview(it)}
                          data-testid={`morning-preview-${it.id}`}
                          className="inline-flex items-center gap-1 px-2.5 h-7 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 hover:border-amber-500/70 text-zinc-200 hover:text-amber-400 rounded-sm btn-tactical text-[10px]"
                        >
                          <Eye size={12} weight="bold" /> Preview
                        </button>
                        <button
                          onClick={() => openEdit(it)}
                          data-testid={`morning-edit-${it.id}`}
                          className="inline-flex items-center gap-1 px-2.5 h-7 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 hover:border-teal-400/70 text-zinc-200 hover:text-teal-300 rounded-sm btn-tactical text-[10px]"
                        >
                          <PencilSimple size={12} weight="bold" /> Edit
                        </button>
                        <button
                          onClick={() => downloadInfographic(it)}
                          disabled={infoLoadingId === it.id}
                          data-testid={`morning-infographic-${it.id}`}
                          className="inline-flex items-center gap-1 px-2.5 h-7 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 hover:border-cyan-400/70 text-zinc-200 hover:text-cyan-300 rounded-sm btn-tactical text-[10px] disabled:opacity-50 disabled:cursor-wait"
                          title="Generate versi infografis (Claude AI)"
                        >
                          {infoLoadingId === it.id
                            ? <><CircleNotch size={12} weight="bold" className="animate-spin" /> Generating...</>
                            : <><ChartBar size={12} weight="bold" /> Infografis</>}
                        </button>
                        <button
                          onClick={() => download(it)}
                          data-testid={`morning-download-${it.id}`}
                          className="inline-flex items-center gap-1 px-2.5 h-7 bg-amber-500 hover:bg-amber-400 text-zinc-950 rounded-sm btn-tactical text-[10px]"
                        >
                          <DownloadSimple size={12} weight="bold" /> Unduh
                        </button>
                        {user?.role === "admin" && (
                          <button
                            onClick={() => del(it.id)}
                            data-testid={`morning-delete-${it.id}`}
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
            {items.length > 7 && (
              <div className="mt-2 flex items-center justify-between text-[10px] font-mono uppercase tracking-wider text-zinc-500">
                <span>Menampilkan 7 terbaru — geser ke bawah untuk arsip lama (total {items.length} arsip)</span>
                <span className="text-amber-500/70">↓ scroll</span>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Preview modal */}
      {previewMeta && (
        <div
          data-testid="morning-preview-modal"
          className="fixed inset-0 z-50 bg-zinc-950/85 backdrop-blur-sm flex flex-col"
          onClick={closePreview}
        >
          <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800 bg-zinc-950">
            <div>
              <p className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">Pratinjau Laporan Pagi</p>
              <h4 className="text-sm font-bold text-amber-400 font-mono">{previewMeta.report_date}</h4>
            </div>
            <button
              onClick={closePreview}
              className="w-8 h-8 rounded-sm bg-zinc-900 hover:bg-red-900 text-zinc-400 hover:text-red-300 flex items-center justify-center"
              data-testid="morning-preview-close"
            >
              <X size={16} weight="bold" />
            </button>
          </div>
          <div
            className="flex-1 overflow-hidden p-4"
            onClick={(e) => e.stopPropagation()}
          >
            {previewLoading ? (
              <div className="flex flex-col items-center justify-center h-full gap-3">
                <CircleNotch size={32} weight="bold" className="text-amber-400 animate-spin" />
                <p className="text-xs uppercase text-zinc-500 font-mono">Memuat PDF...</p>
              </div>
            ) : previewUrl ? (
              <iframe
                src={previewUrl}
                title="preview"
                className="w-full h-full rounded-sm bg-white"
              />
            ) : null}
          </div>
        </div>
      )}
      {/* Edit modal */}
      {editMeta && (
        <div
          data-testid="morning-edit-modal"
          className="fixed inset-0 z-50 bg-zinc-950/85 backdrop-blur-sm flex items-center justify-center p-6"
        >
          <div className="bg-zinc-950 border border-zinc-800 rounded-sm w-full max-w-5xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
              <div>
                <p className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">Edit Laporan Pagi</p>
                <h4 className="text-sm font-bold text-teal-300 font-mono">{editMeta.report_date}</h4>
              </div>
              <button
                onClick={closeEdit}
                className="w-8 h-8 rounded-sm bg-zinc-900 hover:bg-red-900 text-zinc-400 hover:text-red-300 flex items-center justify-center"
                data-testid="morning-edit-close"
              >
                <X size={16} weight="bold" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-5">
              {editLoading ? (
                <div className="flex flex-col items-center justify-center py-20 gap-3">
                  <CircleNotch size={28} weight="bold" className="text-teal-400 animate-spin" />
                  <p className="text-xs uppercase text-zinc-500 font-mono">Memuat konten...</p>
                </div>
              ) : (
                <>
                  <p className="text-xs text-zinc-500 mb-3">
                    Edit teks ringkasan eksekutif & section LID/KONTRA/GAL/MEDMON/GEOINT. PDF akan
                    di-<b className="text-teal-300">rebuild otomatis</b> setelah Anda klik Simpan.
                  </p>
                  <RichEditor
                    value={editHtml}
                    onChange={setEditHtml}
                    testid="morning-rich-editor"
                  />
                </>
              )}
            </div>
            <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-zinc-800 bg-zinc-950">
              <Button
                onClick={closeEdit}
                variant="outline"
                className="h-9 px-4 rounded-sm border-zinc-700 text-xs"
                data-testid="morning-edit-cancel"
              >
                Batal
              </Button>
              <Button
                onClick={saveEdit}
                disabled={editSaving || editLoading}
                data-testid="morning-edit-save"
                className="h-9 px-4 rounded-sm bg-teal-500 hover:bg-teal-400 text-zinc-950 font-bold text-xs"
              >
                {editSaving
                  ? <><CircleNotch size={14} weight="bold" className="mr-1.5 animate-spin" />Menyimpan & rebuild PDF...</>
                  : <><FloppyDisk size={14} weight="bold" className="mr-1.5" />Simpan & Render Ulang</>}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
