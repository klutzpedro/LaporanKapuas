import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, Card } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FilePdf, Robot, Clock, ArrowsClockwise, FloppyDisk } from "@phosphor-icons/react";
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
      toast.error(e.response?.data?.detail || "Gagal membuat ringkasan AI.");
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
      toast.error(e.response?.data?.detail || "Gagal menyimpan.");
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
          const j = JSON.parse(text); msg = j.detail || msg;
        } catch { /* */ }
      } else if (e.response?.data?.detail) msg = e.response.data.detail;
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
            {info?.before_noon && reportDate === info?.report_date && (
              <p className="mt-3 text-[11px] text-amber-400 font-mono leading-relaxed">
                ⚠ Saat ini sebelum 12:00 WIB. Default ke H-1 ({info.report_date}).
              </p>
            )}
          </Card>

          <Card title="Aturan Generate" color="#F59E0B" testid="rules-card">
            <ul className="space-y-3 text-xs text-zinc-300 leading-relaxed">
              <li className="flex gap-2">
                <Clock size={14} className="text-amber-400 shrink-0 mt-0.5" />
                <span>Laporan hari ini hanya dapat di-generate setelah <b className="text-amber-400">12:00 WIB</b>.</span>
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
            }
          >
            {aiHtml ? (
              <RichEditor value={aiHtml} onChange={setAiHtml} testid="ai-rich-editor" />
            ) : (
              <div className="text-sm text-zinc-500 py-12 text-center">
                Belum ada ringkasan AI untuk tanggal <b className="text-amber-400 font-mono">{reportDate || "—"}</b>.
                Klik <b className="text-amber-400">AI Summary</b> untuk membuatnya — lalu Anda bisa mengeditnya di sini.
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
