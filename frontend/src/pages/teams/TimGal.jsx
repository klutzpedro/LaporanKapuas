import { useEffect, useState } from "react";
import { api, apiErrorMsg } from "@/lib/api";
import { usePeriod } from "@/lib/usePeriod";
import { PageHeader, Card, Empty } from "@/components/Shell";
import { PreviousPeriodBanner } from "@/components/PreviousPeriodBanner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import ImageUploader from "@/components/ImageUploader";
import { toast } from "sonner";
import { ItemActions } from "@/components/ActionIcons";
import { Plus, Trash, PencilSimple, X } from "@phosphor-icons/react";

const INP = "bg-zinc-950 border-zinc-800 rounded-sm focus-visible:ring-amber-500/40 focus-visible:border-amber-500 mt-1.5";
const EMPTY = { kategori: "narasi", judul: "", gambar: null, links: [""], keterangan: "" };
const CATEGORY = { narasi: "NARASI", video: "VIDEO", meme: "MEME" };

// Coerce legacy "medsos" stored in older records → "meme" for display & form state.
function normalizeKategori(k) {
  return k === "medsos" ? "meme" : (k || "narasi");
}

export default function TimGal() {
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState(null);
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const { reportDate, periodLabel } = usePeriod();

  async function load() {
    const params = reportDate ? { report_date: reportDate, fallback_previous: true } : {};
    const { data } = await api.get("/gal", { params });
    setItems(data);
  }
  useEffect(() => { load(); }, [reportDate]);
  function set(k, v) { setForm((f) => ({ ...f, [k]: v })); }
  function setLink(i, v) { setForm((f) => { const a = [...f.links]; a[i] = v; return { ...f, links: a }; }); }

  function startEdit(it) {
    setEditId(it.id);
    setForm({
      kategori: normalizeKategori(it.kategori),
      judul: it.judul || "",
      gambar: it.gambar || null,
      links: (it.links && it.links.length) ? it.links : [""],
      keterangan: it.keterangan || "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function cancelEdit() { setEditId(null); setForm(EMPTY); }

  async function submit(e) {
    e.preventDefault(); setBusy(true);
    try {
      const payload = { ...form, links: form.links.filter(Boolean) };
      if (editId) {
        await api.put(`/gal/${editId}`, payload);
        toast.success("Konten diperbarui.");
      } else {
        await api.post("/gal", payload);
        toast.success("Konten tersimpan.");
      }
      setForm(EMPTY); setEditId(null); load();
    } catch (e2) { toast.error(apiErrorMsg(e2, "Gagal menyimpan.")); }
    finally { setBusy(false); }
  }

  async function del(id) {
    if (!confirm("Hapus?")) return;
    await api.delete(`/gal/${id}`);
    if (editId === id) cancelEdit();
    load();
  }

  return (
    <div data-testid="gal-page">
      <PageHeader overline="TIM GAL" title="Konten Penggalangan" subtitle="Narasi · Video · Meme" />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title={editId ? "Edit Konten" : "Form Konten"} color={editId ? "#10B981" : "#3B82F6"} testid="gal-form-card">
          <form onSubmit={submit} className="space-y-4" data-testid="gal-form">
            <Field label="Kategori">
              <Select value={form.kategori} onValueChange={(v) => set("kategori", v)}>
                <SelectTrigger data-testid="gal-kategori" className={INP}><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.keys(CATEGORY).map((k) => <SelectItem key={k} value={k}>{CATEGORY[k]}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Judul"><Input data-testid="gal-judul" value={form.judul} onChange={(e) => set("judul", e.target.value)} required className={INP} /></Field>
            <ImageUploader label="Gambar Konten" value={form.gambar} onChange={(v) => set("gambar", v)} testid="gal-gambar" />

            <div>
              <Label className="overline">Link Konten</Label>
              <div className="space-y-2 mt-1.5">
                {form.links.map((m, i) => (
                  <div key={i} className="flex gap-2">
                    <Input data-testid={`gal-link-${i}`} value={m} onChange={(e) => setLink(i, e.target.value)} placeholder="https://..." className="bg-zinc-950 border-zinc-800 rounded-sm flex-1" />
                    <Button type="button" onClick={() => setForm((f) => ({ ...f, links: f.links.filter((_, idx) => idx !== i) }))} className="bg-zinc-900 hover:bg-red-900 border border-zinc-800 h-9 px-3"><Trash size={12} /></Button>
                  </div>
                ))}
                <Button type="button" onClick={() => setForm((f) => ({ ...f, links: [...f.links, ""] }))} data-testid="gal-add-link" className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 btn-tactical h-8 rounded-sm">
                  <Plus size={12} weight="bold" className="mr-1" /> Tambah Link
                </Button>
              </div>
            </div>
            <Field label="Keterangan"><Textarea data-testid="gal-ket" value={form.keterangan} onChange={(e) => set("keterangan", e.target.value)} className={INP} rows={2} /></Field>

            <div className="flex gap-2">
              <Button type="submit" disabled={busy} data-testid="gal-submit" className="flex-1 bg-amber-500 hover:bg-amber-400 text-zinc-950 btn-tactical rounded-sm h-10">
                {busy ? "Menyimpan..." : (editId ? "Perbarui Konten" : "Simpan Konten")}
              </Button>
              {editId && (
                <Button type="button" onClick={cancelEdit} data-testid="gal-cancel-edit" className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 btn-tactical rounded-sm h-10 px-4">
                  <X size={14} weight="bold" className="mr-1" /> Batal
                </Button>
              )}
            </div>
          </form>
        </Card>

        <Card title="Daftar Laporan Hari Ini" kicker={`PERIODE ${periodLabel}`} testid="gal-list-card">
          <PreviousPeriodBanner items={items} currentDate={reportDate} />
          {items.length === 0 ? <Empty /> : (
            <ul className="space-y-3">
              {items.map((it) => (
                <li key={it.id} className={`bg-zinc-950 border rounded-sm p-3 flex justify-between items-start gap-3 ${editId === it.id ? "border-amber-500/50" : "border-zinc-800"}`} data-testid={`gal-item-${it.id}`}>
                  <div className="flex-1">
                    <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm bg-blue-500/15 text-blue-400">{CATEGORY[normalizeKategori(it.kategori)]}</span>
                    <p className="font-bold text-sm mt-1">{it.judul}</p>
                    <div className="mt-1 space-y-0.5">
                      {(it.links || []).map((l, i) => <a key={i} href={l} target="_blank" rel="noreferrer" className="block text-[11px] font-mono text-amber-400 break-all">{l}</a>)}
                    </div>
                  </div>
                  <ItemActions
                    onEdit={() => startEdit(it)}
                    onDelete={() => del(it.id)}
                    editTestid={`gal-edit-${it.id}`}
                    deleteTestid={`gal-delete-${it.id}`}
                  />
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
