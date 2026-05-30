import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { usePeriod } from "@/lib/usePeriod";
import { PageHeader, Card, Empty } from "@/components/Shell";
import { PreviousPeriodBanner } from "@/components/PreviousPeriodBanner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import ImageUploader from "@/components/ImageUploader";
import { SentimentInput } from "@/components/SentimentInput";
import { toast } from "sonner";
import { Plus, Trash, PencilSimple, X } from "@phosphor-icons/react";

const INP = "bg-zinc-950 border-zinc-800 rounded-sm focus-visible:ring-amber-500/40 focus-visible:border-amber-500 mt-1.5";

const EMPTY = {
  subjek: "Presiden",
  berita: [{ judul: "", link: "", sentiment: "positif" }],
  chart_sumber_image: null,
  sentiment_positif: 0,
  sentiment_negatif: 0,
  sentiment_netral: 0,
  analisa: "",
  rekomendasi: "",
};

export default function TimMedmon() {
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState(null);
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const { reportDate, periodLabel } = usePeriod();

  async function load() {
    const params = reportDate ? { report_date: reportDate, fallback_previous: true } : {};
    const { data } = await api.get("/medmon", { params });
    setItems(data);
  }
  useEffect(() => { load(); }, [reportDate]);
  function set(k, v) { setForm((f) => ({ ...f, [k]: v })); }
  function setBerita(i, k, v) {
    setForm((f) => { const a = [...f.berita]; a[i] = { ...a[i], [k]: v }; return { ...f, berita: a }; });
  }

  function startEdit(it) {
    setEditId(it.id);
    setForm({
      subjek: it.subjek || "Presiden",
      berita: (it.berita && it.berita.length) ? it.berita : [{ judul: "", link: "", sentiment: "positif" }],
      chart_sumber_image: it.chart_sumber_image || null,
      sentiment_positif: it.sentiment_positif || 0,
      sentiment_negatif: it.sentiment_negatif || 0,
      sentiment_netral: it.sentiment_netral || 0,
      analisa: it.analisa || "",
      rekomendasi: it.rekomendasi || "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function cancelEdit() { setEditId(null); setForm(EMPTY); }

  async function submit(e) {
    e.preventDefault();
    const total = (form.sentiment_positif || 0) + (form.sentiment_negatif || 0) + (form.sentiment_netral || 0);
    if (total !== 100) {
      toast.error(`Total sentiment harus 100% (sekarang ${total}%).`);
      return;
    }
    setBusy(true);
    try {
      const payload = { ...form, berita: form.berita.filter((b) => b.judul && b.link) };
      if (editId) {
        await api.put(`/medmon/${editId}`, payload);
        toast.success("Medmon diperbarui.");
      } else {
        await api.post("/medmon", payload);
        toast.success("Medmon tersimpan.");
      }
      setForm(EMPTY); setEditId(null); load();
    } catch (e2) { toast.error(e2.response?.data?.detail || "Gagal menyimpan."); }
    finally { setBusy(false); }
  }

  async function del(id) {
    if (!confirm("Hapus?")) return;
    await api.delete(`/medmon/${id}`);
    if (editId === id) cancelEdit();
    load();
  }

  return (
    <div data-testid="medmon-page">
      <PageHeader overline="TIM MEDMON" title="Media Monitoring" subtitle="Presiden · Panglima TNI · MBG · Subjek lainnya" />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title={editId ? "Edit Medmon" : "Form Medmon"} color={editId ? "#10B981" : "#8B5CF6"} testid="medmon-form-card">
          <form onSubmit={submit} className="space-y-4" data-testid="medmon-form">
            <Field label="Subjek">
              <div className="flex gap-2">
                <Input data-testid="medmon-subjek" value={form.subjek} onChange={(e) => set("subjek", e.target.value)} className={`${INP} flex-1`} list="medmon-subjects" />
                <datalist id="medmon-subjects">
                  <option value="Presiden" />
                  <option value="Panglima TNI" />
                  <option value="MBG" />
                </datalist>
              </div>
            </Field>

            <div>
              <Label className="overline">Berita (Judul + Link + Sentiment)</Label>
              <div className="space-y-2 mt-1.5">
                {form.berita.map((b, i) => (
                  <div key={i} className="grid grid-cols-12 gap-2 items-start">
                    <Input data-testid={`medmon-berita-judul-${i}`} placeholder="Judul" value={b.judul} onChange={(e) => setBerita(i, "judul", e.target.value)} className="bg-zinc-950 border-zinc-800 rounded-sm col-span-5" />
                    <Input data-testid={`medmon-berita-link-${i}`} placeholder="Link" value={b.link} onChange={(e) => setBerita(i, "link", e.target.value)} className="bg-zinc-950 border-zinc-800 rounded-sm col-span-4" />
                    <Select value={b.sentiment} onValueChange={(v) => setBerita(i, "sentiment", v)}>
                      <SelectTrigger className="bg-zinc-950 border-zinc-800 rounded-sm col-span-2" data-testid={`medmon-berita-sentiment-${i}`}><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="positif">Positif</SelectItem>
                        <SelectItem value="negatif">Negatif</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button type="button" onClick={() => setForm((f) => ({ ...f, berita: f.berita.filter((_, idx) => idx !== i) }))} className="bg-zinc-900 hover:bg-red-900 border border-zinc-800 h-9 px-2 col-span-1"><Trash size={12} /></Button>
                  </div>
                ))}
                <Button type="button" onClick={() => setForm((f) => ({ ...f, berita: [...f.berita, { judul: "", link: "", sentiment: "positif" }] }))} data-testid="medmon-add-berita" className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 btn-tactical h-8 rounded-sm">
                  <Plus size={12} weight="bold" className="mr-1" /> Tambah Berita
                </Button>
              </div>
            </div>

            <SentimentInput
              value={{ positif: form.sentiment_positif, negatif: form.sentiment_negatif, netral: form.sentiment_netral }}
              onChange={(v) => setForm((f) => ({ ...f, sentiment_positif: v.positif, sentiment_negatif: v.negatif, sentiment_netral: v.netral }))}
              testid="medmon-sentiment"
            />
            <ImageUploader label="Chart Sumber Berita" value={form.chart_sumber_image} onChange={(v) => set("chart_sumber_image", v)} testid="medmon-chart-sumber" />
            <Field label="Analisa"><Textarea data-testid="medmon-analisa" value={form.analisa} onChange={(e) => set("analisa", e.target.value)} className={INP} rows={3} /></Field>
            <Field label="Rekomendasi"><Textarea data-testid="medmon-rekomendasi" value={form.rekomendasi} onChange={(e) => set("rekomendasi", e.target.value)} className={INP} rows={2} /></Field>

            <div className="flex gap-2">
              <Button type="submit" disabled={busy} data-testid="medmon-submit" className="flex-1 bg-amber-500 hover:bg-amber-400 text-zinc-950 btn-tactical rounded-sm h-10">
                {busy ? "Menyimpan..." : (editId ? "Perbarui Medmon" : "Simpan Medmon")}
              </Button>
              {editId && (
                <Button type="button" onClick={cancelEdit} data-testid="medmon-cancel-edit" className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 btn-tactical rounded-sm h-10 px-4">
                  <X size={14} weight="bold" className="mr-1" /> Batal
                </Button>
              )}
            </div>
          </form>
        </Card>

        <Card title="Daftar Laporan Hari Ini" kicker={`PERIODE ${periodLabel}`} testid="medmon-list-card">
          <PreviousPeriodBanner items={items} currentDate={reportDate} />
          {items.length === 0 ? <Empty /> : (
            <ul className="space-y-3">
              {items.map((it) => {
                const pos = (it.berita || []).filter((b) => b.sentiment === "positif").length;
                const neg = (it.berita || []).filter((b) => b.sentiment === "negatif").length;
                return (
                  <li key={it.id} className={`bg-zinc-950 border rounded-sm p-3 ${editId === it.id ? "border-amber-500/50" : "border-zinc-800"}`} data-testid={`medmon-item-${it.id}`}>
                    <div className="flex items-center justify-between">
                      <p className="font-bold text-sm uppercase">{it.subjek}</p>
                      <div className="flex gap-2 text-xs font-mono items-center">
                        <span className="text-emerald-400">+{pos}</span>
                        <span className="text-red-400">-{neg}</span>
                        <button onClick={() => startEdit(it)} data-testid={`medmon-edit-${it.id}`} className="text-zinc-500 hover:text-amber-400 p-1" title="Edit"><PencilSimple size={14} weight="bold" /></button>
                        <button onClick={() => del(it.id)} data-testid={`medmon-delete-${it.id}`} className="text-zinc-500 hover:text-red-400 p-1" title="Hapus"><Trash size={14} weight="bold" /></button>
                      </div>
                    </div>
                    <p className="text-xs text-zinc-400 mt-1 line-clamp-2">{it.analisa}</p>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}

function Field({ label, children }) { return (<div><Label className="overline">{label}</Label>{children}</div>); }
