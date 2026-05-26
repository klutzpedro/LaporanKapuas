import { useEffect, useState } from "react";
import { api, COG_LABEL, COG_COLOR } from "@/lib/api";
import { PageHeader, Card, Empty } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import ImageUploader from "@/components/ImageUploader";
import { toast } from "sonner";
import { Plus, Trash } from "@phosphor-icons/react";

const EMPTY = {
  cog: "aceh",
  judul: "",
  link: "",
  fakta: "",
  analisa: "",
  tindakan: "",
  rekomendasi: "",
  sentiment_label: "neutral",
  sentiment_image: null,
};

export default function TimLid() {
  const [form, setForm] = useState(EMPTY);
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);

  async function load() {
    const { data } = await api.get("/lid");
    setItems(data);
  }
  useEffect(() => { load(); }, []);

  function set(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/lid", form);
      toast.success("Berita LID tersimpan.");
      setForm(EMPTY);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Gagal menyimpan.");
    } finally { setBusy(false); }
  }

  async function del(id) {
    if (!confirm("Hapus berita ini?")) return;
    await api.delete(`/lid/${id}`);
    load();
  }

  return (
    <div data-testid="lid-page">
      <PageHeader overline="TIM LID" title="Input Berita Trending" subtitle="4 berita per hari: 3 COG (ACEH, JAKARTA, PAPUA) + 1 INTERNASIONAL" />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Form Input" color="#F59E0B" testid="lid-form-card">
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
            <ImageUploader label="Gambar Sentiment" value={form.sentiment_image} onChange={(v) => set("sentiment_image", v)} testid="lid-sentiment-image" />
            <Button type="submit" disabled={busy} data-testid="lid-submit" className="w-full bg-amber-500 hover:bg-amber-400 text-zinc-950 btn-tactical rounded-sm h-10">
              <Plus size={14} weight="bold" className="mr-2" /> {busy ? "Menyimpan..." : "Simpan Laporan"}
            </Button>
          </form>
        </Card>

        <Card title="Daftar Laporan LID (Hari Ini)" testid="lid-list-card">
          {items.length === 0 ? <Empty /> : (
            <ul className="space-y-3">
              {items.map((it) => (
                <li key={it.id} className="border-l-2 pl-3 py-1" style={{ borderColor: COG_COLOR[it.cog] }} data-testid={`lid-item-${it.id}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm" style={{ background: `${COG_COLOR[it.cog]}22`, color: COG_COLOR[it.cog] }}>{COG_LABEL[it.cog]}</span>
                      <p className="text-sm font-bold mt-1">{it.judul}</p>
                      {it.link && <a href={it.link} target="_blank" rel="noreferrer" className="text-[11px] font-mono text-amber-400 break-all">{it.link}</a>}
                      <p className="text-xs text-zinc-400 mt-1 line-clamp-2">{it.analisa}</p>
                    </div>
                    <button onClick={() => del(it.id)} data-testid={`lid-delete-${it.id}`} className="text-zinc-500 hover:text-red-400"><Trash size={14} weight="bold" /></button>
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
