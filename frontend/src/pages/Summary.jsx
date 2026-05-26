import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, Card } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FilePdf, Robot, Clock, ArrowsClockwise } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function SummaryPage() {
  const [info, setInfo] = useState(null);
  const [reportDate, setReportDate] = useState("");
  const [aiText, setAiText] = useState("");
  const [aiMeta, setAiMeta] = useState(null);
  const [busyAI, setBusyAI] = useState(false);
  const [busyPDF, setBusyPDF] = useState(false);

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
        setAiText(s.data?.summary || "");
        setAiMeta(s.data?.generated_at ? { generated_at: s.data.generated_at } : null);
      } catch {
        setAiText("");
      }
    })();
  }, [reportDate]);

  async function generateAI() {
    setBusyAI(true);
    try {
      const r = await api.post("/summary/ai", { report_date: reportDate });
      setAiText(r.data.summary);
      toast.success("Ringkasan AI berhasil dibuat dari data semua tim.");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Gagal membuat ringkasan AI.");
    } finally {
      setBusyAI(false);
    }
  }

  async function downloadPDF() {
    setBusyPDF(true);
    try {
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
          msg = j.detail || msg;
        } catch { /* */ }
      } else if (e.response?.data?.detail) {
        msg = e.response.data.detail;
      }
      toast.error(msg);
    } finally {
      setBusyPDF(false);
    }
  }

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
              className="h-10 rounded-sm bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 btn-tactical"
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
              className="bg-zinc-950 border-zinc-800 rounded-sm mt-1.5 h-10"
              data-testid="report-date-input"
            />
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={() => setReportDate(info?.report_date || "")}
                data-testid="date-default"
                className="flex-1 text-[10px] font-mono uppercase tracking-wider py-1.5 px-2 border border-zinc-800 hover:border-amber-500/70 hover:text-amber-400 text-zinc-400 rounded-sm transition-colors"
              >
                <ArrowsClockwise size={11} className="inline mr-1" />
                Default ({info?.report_date || "—"})
              </button>
            </div>
            {info?.before_noon && reportDate === info?.report_date && (
              <p className="mt-3 text-[11px] text-amber-400 font-mono leading-relaxed">
                ⚠ Saat ini sebelum 12:00 WIB. Default tanggal otomatis ke H-1 ({info.report_date}).
              </p>
            )}
          </Card>

          <Card title="Aturan Generate" color="#F59E0B" testid="rules-card">
            <ul className="space-y-3 text-xs text-zinc-300 leading-relaxed">
              <li className="flex gap-2">
                <Clock size={14} className="text-amber-400 shrink-0 mt-0.5" />
                <span>Laporan tanggal hari ini hanya dapat di-generate setelah <b className="text-amber-400">12:00 WIB</b>.</span>
              </li>
              <li className="flex gap-2">
                <Robot size={14} className="text-amber-400 shrink-0 mt-0.5" />
                <span>AI Summary menggabungkan input <b>SEMUA TIM</b> (LID, Kontra, GAL, Medmon, Geoint, Piket) menjadi satu narasi padat &lt;320 kata.</span>
              </li>
              <li className="flex gap-2">
                <FilePdf size={14} className="text-amber-400 shrink-0 mt-0.5" />
                <span>Output PDF max <b>2 halaman</b>. Hal 1 = Summary AI + KPI + 4 mini-COG. Hal 2 = Data dukung (gambar pie/chart/peta/SNA).</span>
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
            title="Pratinjau Ringkasan AI"
            kicker={aiMeta?.generated_at ? `Dibuat: ${new Date(aiMeta.generated_at).toLocaleString("id-ID")}` : "BELUM ADA"}
            color="#8B5CF6"
            testid="ai-preview-card"
          >
            {aiText ? (
              <pre className="whitespace-pre-wrap text-sm text-zinc-200 leading-relaxed font-sans">{aiText}</pre>
            ) : (
              <div className="text-sm text-zinc-500 py-12 text-center">
                Belum ada ringkasan AI untuk tanggal <b className="text-amber-400 font-mono">{reportDate || "—"}</b>.
                Klik <b className="text-amber-400">AI Summary</b> untuk membuatnya.
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
