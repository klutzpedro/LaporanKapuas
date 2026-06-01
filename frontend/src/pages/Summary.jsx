import { useEffect, useState } from "react";
import { api, apiErrorMsg } from "@/lib/api";
import { PageHeader, Card } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FilePdf, Robot, Clock, ArrowsClockwise, FloppyDisk, Plus, Sparkle, Trash } from "@phosphor-icons/react";
import { toast } from "sonner";
import RichEditor from "@/components/RichEditor";
import { marked } from "marked";

function mdToHtml(md) {
  if (!md) return "";
  // If already looks like HTML, return as-is
  if (/<\w+[^>]*>/.test(md)) return md;
  try { return marked.parse(md, { breaks: true }); } catch { return md; }
}

export default function SummaryPage() {
  const [info, setInfo] = useState(null);
  const [reportDate, setReportDate] = useState("");
  const [aiHtml, setAiHtml] = useState("");
  const [originalHtml, setOriginalHtml] = useState("");
  const [aiMeta, setAiMeta] = useState(null);
  const [busyAI, setBusyAI] = useState(false);
  const [busyPDF, setBusyPDF] = useState(false);
  const [busySave, setBusySave] = useState(false);

  useEffect(() => {
    (async () => {
      const i = await api.get("/daily/info");
      setInfo(i.data);
      setReportDate(i.data.report_date);
    })();
  }, []);

  useEffect(() => {
    if (!reportDate) return;
    (async () => {
      try {
        const s = await api.get("/summary/ai", { params: { report_date: reportDate } });
        const initial = s.data?.html || mdToHtml(s.data?.summary || "");
        setAiHtml(initial);
        setOriginalHtml(initial);
        setAiMeta(s.data?.generated_at ? { generated_at: s.data.generated_at, edited_at: s.data.edited_at } : null);
      } catch {
        setAiHtml("");
        setOriginalHtml("");
      }
    })();
  }, [reportDate]);

  async function generateAI() {
    setBusyAI(true);
    try {
      const r = await api.post("/summary/ai", { report_date: reportDate });
      const html = r.data?.html || mdToHtml(r.data?.summary || "");
      setAiHtml(html);
      setOriginalHtml(html);
      toast.success("Ringkasan AI berhasil dibuat dari data semua tim.");
    } catch (e) {
      toast.error(apiErrorMsg(e, "Gagal membuat ringkasan AI."));
    } finally {
      setBusyAI(false);
    }
  }

  async function saveEdits() {
    setBusySave(true);
    try {
      await api.patch("/summary/ai", { report_date: reportDate, html: aiHtml });
      setOriginalHtml(aiHtml);
      toast.success("Perubahan ringkasan tersimpan.");
    } catch (e) {
      toast.error(apiErrorMsg(e, "Gagal menyimpan."));
    } finally {
      setBusySave(false);
    }
  }

  function startManual() {
    const template = `<h3>Ringkasan Manual</h3><p>Tulis ringkasan eksekutif di sini.</p><p><strong>Highlight:</strong> ...</p><p><strong>Rekomendasi:</strong> ...</p>`;
    setAiHtml(template);
    setOriginalHtml("");
  }

  async function deleteSummary() {
    if (!confirm("Hapus ringkasan untuk tanggal ini?")) return;
    setBusySave(true);
    try {
      await api.patch("/summary/ai", { report_date: reportDate, html: "" });
      setAiHtml("");
      setOriginalHtml("");
      toast.success("Ringkasan dihapus.");
    } catch (e) {
      toast.error(apiErrorMsg(e, "Gagal menghapus."));
    } finally {
      setBusySave(false);
    }
  }

  async function downloadPDF() {
    setBusyPDF(true);
    try {
      // Auto-save edits before downloading
      if (aiHtml && aiHtml !== originalHtml) {
        await api.patch("/summary/ai", { report_date: reportDate, html: aiHtml });
        setOriginalHtml(aiHtml);
      }
      const res = await api.get("/pdf", { params: { report_date: reportDate }, responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `BAIS_Summary_${reportDate}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast.success("PDF berhasil diunduh & disimpan ke arsip.");
    } catch (e) {
      let msg = "Gagal generate PDF.";
      if (e.response?.data instanceof Blob) {
        try {
          const text = await e.response.data.text();
          const j = JSON.parse(text);
          msg = typeof j.detail === "string" ? j.detail : msg;
        } catch { /* */ }
      } else {
        msg = apiErrorMsg(e, msg);
      }
      toast.error(msg);
    } finally {
      setBusyPDF(false);
    }
  }

  const isDirty = aiHtml && aiHtml !== originalHtml;

  return (
    <div data-testid="summary-page">
      <PageHeader
        overline="OUTPUT // SUMMARY 2 HALAMAN"
        title="Generate Laporan"
        subtitle={info ? `WIB sekarang: ${new Date(info.now_wib).toLocaleString("id-ID", { hour12: false })}` : ""}
        right={
          <>
            <Button
              onClick={generateAI}
              disabled={busyAI || !reportDate}
              data-testid="generate-ai-button"
              className="h-10 rounded-sm bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 btn-tactical text-zinc-100"
            >
              <Robot size={14} weight="bold" className="mr-2" />
              {busyAI ? "Membuat..." : "AI Summary"}
            </Button>
            <Button
              onClick={downloadPDF}
              disabled={busyPDF || !reportDate}
              data-testid="download-pdf-button"
              className="h-10 rounded-sm bg-amber-500 hover:bg-amber-400 text-zinc-950 btn-tactical"
            >
              <FilePdf size={14} weight="bold" className="mr-2" />
              {busyPDF ? "Generating..." : "Download PDF"}
            </Button>
          </>
        }
        testid="summary-header"
      />

      <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <Card title="Pilih Tanggal Laporan" color="#F59E0B" testid="date-picker-card">
            <Label className="overline">Tanggal Laporan</Label>
            <Input
              type="date"
              value={reportDate}
              onChange={(e) => setReportDate(e.target.value)}
              className="bg-zinc-950 border-zinc-800 rounded-sm mt-1.5 w-full font-mono text-sm"
              data-testid="report-date-input"
            />
            <button
              type="button"
              onClick={() => setReportDate(info?.report_date || "")}
              data-testid="date-default"
              className="mt-3 w-full text-[10px] font-mono uppercase tracking-wider py-2 px-2 border border-zinc-800 hover:border-amber-500/70 hover:text-amber-400 text-zinc-400 rounded-sm transition-colors flex items-center justify-center gap-1.5"
            >
              <ArrowsClockwise size={11} />
              Default ({info?.report_date || "—"})
            </button>
            {(info?.before_cutoff ?? info?.before_noon) && reportDate === info?.report_date && (
              <p className="mt-3 text-[11px] text-amber-400 font-mono leading-relaxed">
                ⚠ Saat ini sebelum {String(info?.cutoff_hour ?? 9).padStart(2,"0")}:{String(info?.cutoff_minute ?? 0).padStart(2,"0")} WIB. Default ke H-1 ({info.report_date}).
              </p>
            )}
          </Card>

          <Card title="Aturan Generate" color="#F59E0B" testid="rules-card">
            <ul className="space-y-3 text-xs text-zinc-300 leading-relaxed">
              <li className="flex gap-2">
                <Clock size={14} className="text-amber-400 shrink-0 mt-0.5" />
                <span>Laporan hari ini hanya dapat di-generate setelah <b className="text-amber-400">{String(info?.cutoff_hour ?? 9).padStart(2,"0")}:{String(info?.cutoff_minute ?? 0).padStart(2,"0")} WIB</b>.</span>
              </li>
              <li className="flex gap-2">
                <Robot size={14} className="text-amber-400 shrink-0 mt-0.5" />
                <span>AI menggabungkan input <b>SEMUA TIM</b> menjadi narasi padat &lt;320 kata.</span>
              </li>
              <li className="flex gap-2">
                <FilePdf size={14} className="text-amber-400 shrink-0 mt-0.5" />
                <span>Anda dapat <b className="text-amber-400">mengedit</b> ringkasan (bold, italic, underline, warna, font, ukuran) sebelum download PDF.</span>
              </li>
              <li className="flex gap-2">
                <FilePdf size={14} className="text-amber-400 shrink-0 mt-0.5" />
                <span>Setiap PDF yang di-generate otomatis tersimpan di <b className="text-amber-400">Arsip Laporan</b>.</span>
              </li>
            </ul>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <Card
            title="Pratinjau & Edit Ringkasan AI"
            kicker={aiMeta?.edited_at
              ? `Diedit: ${new Date(aiMeta.edited_at).toLocaleString("id-ID")}`
              : aiMeta?.generated_at
                ? `Dibuat: ${new Date(aiMeta.generated_at).toLocaleString("id-ID")}`
                : "BELUM ADA"}
            color="#8B5CF6"
            testid="ai-preview-card"
            right={
              <div className="flex items-center gap-2">
                {aiHtml ? (
                  <Button
                    onClick={deleteSummary}
                    disabled={busySave}
                    data-testid="delete-summary-button"
                    className="h-8 rounded-sm btn-tactical bg-zinc-900 hover:bg-red-900/50 border border-zinc-800 hover:border-red-500/60 text-zinc-400 hover:text-red-400"
                    title="Hapus ringkasan"
                  >
                    <Trash size={12} weight="bold" />
                  </Button>
                ) : null}
                <Button
                  onClick={saveEdits}
                  disabled={busySave || !isDirty || !aiHtml}
                  data-testid="save-edits-button"
                  className={`h-8 rounded-sm btn-tactical ${
                    isDirty
                      ? "bg-amber-500 hover:bg-amber-400 text-zinc-950"
                      : "bg-zinc-900 border border-zinc-800 text-zinc-500 cursor-not-allowed"
                  }`}
                >
                  <FloppyDisk size={12} weight="bold" className="mr-1.5" />
                  {busySave ? "Menyimpan..." : isDirty ? "Simpan" : "Tersimpan"}
                </Button>
              </div>
            }
          >
            {aiHtml ? (
              <RichEditor value={aiHtml} onChange={setAiHtml} testid="ai-rich-editor" />
            ) : (
              <div className="py-10 flex flex-col items-center gap-4">
                <p className="text-sm text-zinc-500 text-center max-w-md">
                  Belum ada ringkasan untuk tanggal <b className="text-amber-400 font-mono">{reportDate || "—"}</b>.
                </p>
                <div className="flex gap-2">
                  <Button
                    onClick={startManual}
                    data-testid="start-manual-button"
                    className="h-9 px-4 rounded-sm btn-tactical bg-amber-500 hover:bg-amber-400 text-zinc-950 font-bold"
                  >
                    <Plus size={14} weight="bold" className="mr-2" />
                    Tulis Manual
                  </Button>
                  <Button
                    onClick={generateAI}
                    disabled={busyAI}
                    data-testid="start-ai-button"
                    className="h-9 px-4 rounded-sm btn-tactical bg-violet-600 hover:bg-violet-500 text-white"
                  >
                    <Sparkle size={14} weight="bold" className="mr-2" />
                    {busyAI ? "Memproses..." : "AI Summary"}
                  </Button>
                </div>
                <p className="text-[10px] text-zinc-600 uppercase tracking-wider">
                  Tulis Manual = ketik bebas · AI Summary = generate dari data tim
                </p>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
