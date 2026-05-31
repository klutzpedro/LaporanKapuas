import { useEffect, useState } from "react";
import { api, COG_LABEL, COG_COLOR } from "@/lib/api";
import { usePeriod } from "@/lib/usePeriod";
import { PageHeader, Card, Empty } from "@/components/Shell";
import { PreviousPeriodBanner } from "@/components/PreviousPeriodBanner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SentimentInput } from "@/components/SentimentInput";
import { toast } from "sonner";
import { Plus, Trash, PencilSimple, X } from "@phosphor-icons/react";

const EMPTY = {
  cog: "aceh",
  judul: "",
  link: "",
  fakta: "",
  analisa: "",
  tindakan: "",
  rekomendasi: "",
  sentiment_positif: 0,
  sentiment_negatif: 0,
  sentiment_netral: 0,
};

export default function TimLid() {
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState(null);
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const { reportDate, periodLabel } = usePeriod();

  async function load() {
    const params = reportDate ? { report_date: reportDate, fallback_previous: true } : {};
    const { data } = await api.get("/lid", { params });
    setItems(data);
  }
  useEffect(() => { load(); }, [reportDate]);

  function set(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  function startEdit(it) {
    setEditId(it.id);
    setForm({
      cog: it.cog || "aceh",
      judul: it.judul || "",
      link: it.link || "",
      fakta: it.fakta || "",
      analisa: it.analisa || "",
      tindakan: it.tindakan || "",
      rekomendasi: it.rekomendasi || "",
      sentiment_positif: it.sentiment_positif || 0,
      sentiment_negatif: it.sentiment_negatif || 0,
      sentiment_netral: it.sentiment_netral || 0,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEdit() { setEditId(null); setForm(EMPTY); }

  async function submit(e) {
    e.preventDefault();
    const total = (form.sentiment_positif || 0) + (form.sentiment_negatif || 0) + (form.sentiment_netral || 0);
    if (Math.abs(total - 100) >= 0.01) {
      toast.error(`Total sentiment harus 100% (sekarang ${total.toFixed(2)}%).`);
      return;
    }
    setBusy(true);
    try {
      if (editId) {
        await api.put(`/lid/${editId}`, form);
        toast.success("Berita LID diperbarui.");
      } else {
        await api.post("/lid", form);
        toast.success("Berita LID tersimpan.");
      }
      setForm(EMPTY); setEditId(null);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Gagal menyimpan.");
    } finally { setBusy(false); }
  }

  async function del(id) {
    if (!confirm("Hapus berita ini?")) return;
    await api.delete(`/lid/${id}`);
    if (editId === id) cancelEdit();
    load();
  }

  return (
    <div data-testid="lid-page">
      <PageHeader overline="TIM LID" title="Input Berita Trending" subtitle="4 berita per hari: 3 COG (ACEH, JAKARTA, PAPUA) + 1 INTERNASIONAL" />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title={editId ? "Edit Laporan" : "Form Input"} color={editId ? "#10B981" : "#F59E0B"} testid="lid-form-card">
          <form onSubmit={submit} className="space-y-4" data-testid="lid-form">
            <div>
              <Label className="overline">Center of Gravity</Label>
              <Select value={form.cog} onValueChange={(v) => set("cog", v)}>
                <SelectTrigger data-testid="lid-cog-select" className="bg-zinc-950 border-zinc-800 rounded-sm mt-1.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.keys(COG_LABEL).map((k) => (
                    <SelectItem key={k} value={k}>{COG_LABEL[k]}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Field label="Judul Berita"><Input data-testid="lid-judul" value={form.judul} onChange={(e) => set("judul", e.target.value)} required className={INP} /></Field>
            <Field label="Link"><Input data-testid="lid-link" value={form.link} onChange={(e) => set("link", e.target.value)} required className={INP} /></Field>
            <Field label="Fakta"><Textarea data-testid="lid-fakta" value={form.fakta} onChange={(e) => set("fakta", e.target.value)} className={INP} rows={2} /></Field>
            <Field label="Analisa"><Textarea data-testid="lid-analisa" value={form.analisa} onChange={(e) => set("analisa", e.target.value)} className={INP} rows={3} /></Field>
            <Field label="Tindakan Satgas"><Textarea data-testid="lid-tindakan" value={form.tindakan} onChange={(e) => set("tindakan", e.target.value)} className={INP} rows={2} /></Field>
            <Field label="Rekomendasi BAIS"><Textarea data-testid="lid-rekomendasi" value={form.rekomendasi} onChange={(e) => set("rekomendasi", e.target.value)} className={INP} rows={2} /></Field>
            <SentimentInput
              value={{ positif: form.sentiment_positif, negatif: form.sentiment_negatif, netral: form.sentiment_netral }}
              onChange={(v) => setForm((f) => ({ ...f, sentiment_positif: v.positif, sentiment_negatif: v.negatif, sentiment_netral: v.netral }))}
              testid="lid-sentiment"
            />
            <div className="flex gap-2">
              <Button type="submit" disabled={busy} data-testid="lid-submit" className="flex-1 bg-amber-500 hover:bg-amber-400 text-zinc-950 btn-tactical rounded-sm h-10">
                {editId ? <PencilSimple size={14} weight="bold" className="mr-2" /> : <Plus size={14} weight="bold" className="mr-2" />}
                {busy ? "Menyimpan..." : (editId ? "Perbarui Laporan" : "Simpan Laporan")}
              </Button>
              {editId && (
                <Button type="button" onClick={cancelEdit} data-testid="lid-cancel-edit" className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 btn-tactical rounded-sm h-10 px-4">
                  <X size={14} weight="bold" className="mr-1" /> Batal
                </Button>
              )}
            </div>
          </form>
        </Card>

        <Card title="Daftar Laporan Hari Ini" kicker={`PERIODE ${periodLabel}`} testid="lid-list-card">
          <PreviousPeriodBanner items={items} currentDate={reportDate} />
          {items.length === 0 ? <Empty /> : (
            <ul className="space-y-3">
              {items.map((it) => (
                <li key={it.id} className={`border-l-2 pl-3 py-1 ${editId === it.id ? "bg-amber-500/5" : ""}`} style={{ borderColor: COG_COLOR[it.cog] }} data-testid={`lid-item-${it.id}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm" style={{ background: `${COG_COLOR[it.cog]}22`, color: COG_COLOR[it.cog] }}>{COG_LABEL[it.cog]}</span>
                      <p className="text-sm font-bold mt-1">{it.judul}</p>
                      {it.link && <a href={it.link} target="_blank" rel="noreferrer" className="text-[11px] font-mono text-amber-400 break-all">{it.link}</a>}
                      <p className="text-xs text-zinc-400 mt-1 line-clamp-2">{it.analisa}</p>
                    </div>
                    <div className="flex gap-1 items-start">
                      <button onClick={() => startEdit(it)} data-testid={`lid-edit-${it.id}`} className="text-zinc-500 hover:text-amber-400 p-1" title="Edit"><PencilSimple size={14} weight="bold" /></button>
                      <button onClick={() => del(it.id)} data-testid={`lid-delete-${it.id}`} className="text-zinc-500 hover:text-red-400 p-1" title="Hapus"><Trash size={14} weight="bold" /></button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}

const INP = "bg-zinc-950 border-zinc-800 rounded-sm focus-visible:ring-amber-500/40 focus-visible:border-amber-500 mt-1.5";

function Field({ label, children }) {
  return (<div><Label className="overline">{label}</Label>{children}</div>);
}
