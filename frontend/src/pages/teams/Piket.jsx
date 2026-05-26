import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, Card, Empty } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import ImageUploader from "@/components/ImageUploader";
import { toast } from "sonner";
import { Trash } from "@phosphor-icons/react";

const INP = "bg-zinc-950 border-zinc-800 rounded-sm focus-visible:ring-amber-500/40 focus-visible:border-amber-500 mt-1.5";
const EMPTY = { satgas: "tek", judul: "", isi: "", gambar: null };
const SATGAS = { tek: "SATGAS TEK", sandi: "SATGAS SANDI", medis: "SATGAS MEDIS" };

export default function Piket() {
  const [form, setForm] = useState(EMPTY);
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);

  async function load() { const { data } = await api.get("/piket"); setItems(data); }
  useEffect(() => { load(); }, []);
  function set(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  async function submit(e) {
    e.preventDefault(); setBusy(true);
    try {
      await api.post("/piket", form);
      toast.success("Laporan piket tersimpan."); setForm(EMPTY); load();
    } catch (e2) { toast.error(e2.response?.data?.detail || "Gagal menyimpan."); }
    finally { setBusy(false); }
  }

  async function del(id) { if (!confirm("Hapus?")) return; await api.delete(`/piket/${id}`); load(); }

  return (
    <div data-testid="piket-page">
      <PageHeader overline="PIKET" title="Laporan Satgas TEK/SANDI/MEDIS" subtitle="Konsolidasi data dari Satgas oleh Piket" />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Form Piket" color="#A1A1AA" testid="piket-form-card">
          <form onSubmit={submit} className="space-y-4" data-testid="piket-form">
            <Field label="Satgas">
              <Select value={form.satgas} onValueChange={(v) => set("satgas", v)}>
                <SelectTrigger data-testid="piket-satgas" className={INP}><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.keys(SATGAS).map((k) => <SelectItem key={k} value={k}>{SATGAS[k]}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Judul"><Input data-testid="piket-judul" value={form.judul} onChange={(e) => set("judul", e.target.value)} required className={INP} /></Field>
            <Field label="Isi Laporan"><Textarea data-testid="piket-isi" value={form.isi} onChange={(e) => set("isi", e.target.value)} className={INP} rows={5} required /></Field>
            <ImageUploader label="Gambar (opsional)" value={form.gambar} onChange={(v) => set("gambar", v)} testid="piket-gambar" />

            <Button type="submit" disabled={busy} data-testid="piket-submit" className="w-full bg-amber-500 hover:bg-amber-400 text-zinc-950 btn-tactical rounded-sm h-10">
              {busy ? "Menyimpan..." : "Simpan Laporan"}
            </Button>
          </form>
        </Card>

        <Card title="Daftar Laporan Piket" testid="piket-list-card">
          {items.length === 0 ? <Empty /> : (
            <ul className="space-y-3">
              {items.map((it) => (
                <li key={it.id} className="bg-zinc-950 border border-zinc-800 rounded-sm p-3" data-testid={`piket-item-${it.id}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm bg-zinc-800 text-zinc-300">{SATGAS[it.satgas]}</span>
                      <p className="font-bold text-sm mt-1">{it.judul}</p>
                      <p className="text-xs text-zinc-400 mt-1 line-clamp-3">{it.isi}</p>
                    </div>
                    <button onClick={() => del(it.id)} data-testid={`piket-delete-${it.id}`} className="text-zinc-500 hover:text-red-400"><Trash size={14} weight="bold" /></button>
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

function Field({ label, children }) { return (<div><Label className="overline">{label}</Label>{children}</div>); }
