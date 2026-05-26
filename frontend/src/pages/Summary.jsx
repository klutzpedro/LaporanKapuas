import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, Card } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { FilePdf, Robot, Clock } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function SummaryPage() {
  const [info, setInfo] = useState(null);
  const [aiText, setAiText] = useState("");
  const [busyAI, setBusyAI] = useState(false);
  const [busyPDF, setBusyPDF] = useState(false);

  useEffect(() => {
    (async () => {
      const i = await api.get("/daily/info");
      setInfo(i.data);
      const s = await api.get("/summary/ai", { params: { report_date: i.data.report_date } });
      if (s.data?.summary) setAiText(s.data.summary);
    })();
  }, []);

  async function generateAI() {
    setBusyAI(true);
    try {
      const r = await api.post("/summary/ai", { report_date: info.report_date });
      setAiText(r.data.summary);
      toast.success("Ringkasan AI berhasil dibuat.");
    } catch (e) {
      toast.error("Gagal membuat ringkasan AI.");
    } finally {
      setBusyAI(false);
    }
  }

  async function downloadPDF() {
    setBusyPDF(true);
    try {
      const res = await api.get("/pdf", { params: { report_date: info.report_date }, responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `BAIS_Summary_${info.report_date}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("PDF berhasil diunduh.");
    } catch (e) {
      const msg = e.response?.data?.detail || "Gagal generate PDF.";
      // If response is blob, try parse
      if (e.response?.data instanceof Blob) {
        try {
          const text = await e.response.data.text();
          const j = JSON.parse(text);
          toast.error(j.detail || msg);
        } catch {
          toast.error(msg);
        }
      } else {
        toast.error(msg);
      }
    } finally {
      setBusyPDF(false);
    }
  }

  return (
    <div data-testid="summary-page">
      <PageHeader
        overline="OUTPUT // SUMMARY 2 HALAMAN"
        title="Generate Laporan"
        subtitle={info ? `Tanggal: ${info.report_date} • WIB: ${new Date(info.now_wib).toLocaleTimeString("id-ID")}` : ""}
        right={
          <>
            <Button
              onClick={generateAI}
              disabled={busyAI || !info}
              data-testid="generate-ai-button"
              className="h-10 rounded-sm bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 btn-tactical"
            >
              <Robot size={14} weight="bold" className="mr-2" />
              {busyAI ? "Membuat..." : "AI Summary"}
            </Button>
            <Button
              onClick={downloadPDF}
              disabled={busyPDF || !info}
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
          <Card title="Aturan Generate" color="#F59E0B" testid="rules-card">
            <ul className="space-y-3 text-xs text-zinc-300 leading-relaxed">
              <li className="flex gap-2">
                <Clock size={14} className="text-amber-400 shrink-0 mt-0.5" />
                <span>Laporan tanggal hari ini hanya dapat di-generate setelah <b className="text-amber-400">12:00 WIB</b>.</span>
              </li>
              <li className="flex gap-2">
                <Clock size={14} className="text-amber-400 shrink-0 mt-0.5" />
                <span>Sebelum 12:00 WIB, sistem otomatis menarik data tanggal sebelumnya (H-1).</span>
              </li>
              <li className="flex gap-2">
                <Robot size={14} className="text-amber-400 shrink-0 mt-0.5" />
                <span>AI Summary disusun oleh <b>Claude Sonnet 4.5</b> berdasar input semua tim.</span>
              </li>
              <li className="flex gap-2">
                <FilePdf size={14} className="text-amber-400 shrink-0 mt-0.5" />
                <span>Output PDF maksimal <b>2 halaman</b>: hal 1 infografis 4 COG, hal 2 narasi + medmon/kontra/geoint.</span>
              </li>
            </ul>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <Card title="Pratinjau Ringkasan AI" kicker="NARASI" color="#8B5CF6" testid="ai-preview-card">
            {aiText ? (
              <pre className="whitespace-pre-wrap text-sm text-zinc-200 leading-relaxed font-sans">{aiText}</pre>
            ) : (
              <div className="text-sm text-zinc-500 py-12 text-center">
                Belum ada ringkasan AI. Klik <b className="text-amber-400">AI Summary</b> untuk membuatnya.
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
