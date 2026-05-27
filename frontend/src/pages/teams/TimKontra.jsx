import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { usePeriod } from "@/lib/usePeriod";
import { PageHeader, Card, Empty } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import ImageUploader from "@/components/ImageUploader";
import { toast } from "sonner";
import { Plus, Trash, PencilSimple, X } from "@phosphor-icons/react";

const INP = "bg-zinc-950 border-zinc-800 rounded-sm focus-visible:ring-amber-500/40 focus-visible:border-amber-500 mt-1.5";
const EMPTY = {
  sumber: "to_satgas", tipe: "perorangan", nama_to: "", data_diri: "",
  medsos: [""], sna_image: null, lainnya_image: null, keterangan: "",
};

export default function TimKontra() {
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState(null);
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const { reportDate, periodLabel } = usePeriod();

  async function load() {
    const params = reportDate ? { report_date: reportDate } : {};
    const { data } = await api.get("/kontra", { params });
    setItems(data);
  }
  useEffect(() => { load(); }, [reportDate]);
  function set(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  function setMedsos(i, v) {
    setForm((f) => { const m = [...f.medsos]; m[i] = v; return { ...f, medsos: m }; });
  }
  function addMedsos() { setForm((f) => ({ ...f, medsos: [...f.medsos, ""] })); }
  function rmMedsos(i) { setForm((f) => ({ ...f, medsos: f.medsos.filter((_, idx) => idx !== i) })); }

  function startEdit(it) {
    setEditId(it.id);
    setForm({
      sumber: it.sumber || "to_satgas",
      tipe: it.tipe || "perorangan",
      nama_to: it.nama_to || "",
      data_diri: it.data_diri || "",
      medsos: (it.medsos && it.medsos.length) ? it.medsos : [""],
      sna_image: it.sna_image || null,
      lainnya_image: it.lainnya_image || null,
      keterangan: it.keterangan || "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function cancelEdit() { setEditId(null); setForm(EMPTY); }

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = { ...form, medsos: form.medsos.filter(Boolean) };
      if (editId) {
        await api.put(`/kontra/${editId}`, payload);
        toast.success("Profiling diperbarui.");
      } else {
        await api.post("/kontra", payload);
        toast.success("Profiling tersimpan.");
      }
      setForm(EMPTY); setEditId(null); load();
    } catch (e2) { toast.error(e2.response?.data?.detail || "Gagal menyimpan."); }
    finally { setBusy(false); }
  }

  async function del(id) {
    if (!confirm("Hapus?")) return;
    await api.delete(`/kontra/${id}`);
    if (editId === id) cancelEdit();
    load();
  }

  return (
    <div data-testid="kontra-page">
      <PageHeader overline="TIM KONTRA" title="Profiling Target Operasi" subtitle="Minimal 3 profiling: TO Satgas (resmi) atau TO Internal" />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title={editId ? "Edit Profiling" : "Form Profiling"} color={editId ? "#10B981" : "#EF4444"} testid="kontra-form-card">
          <form onSubmit={submit} className="space-y-4" data-testid="kontra-form">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="overline">Sumber TO</Label>
                <Select value={form.sumber} onValueChange={(v) => set("sumber", v)}>
                  <SelectTrigger data-testid="kontra-sumber" className={INP}><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="to_satgas">TO Satgas (Resmi)</SelectItem>
                    <SelectItem value="to_internal">TO Internal</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="overline">Tipe</Label>
                <Select value={form.tipe} onValueChange={(v) => set("tipe", v)}>
                  <SelectTrigger data-testid="kontra-tipe" className={INP}><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="perorangan">Perorangan</SelectItem>
                    <SelectItem value="group">Group/Organisasi</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Field label="Nama TO"><Input data-testid="kontra-nama" value={form.nama_to} onChange={(e) => set("nama_to", e.target.value)} required className={INP} /></Field>
            <Field label="Data Diri"><Textarea data-testid="kontra-data" value={form.data_diri} onChange={(e) => set("data_diri", e.target.value)} className={INP} rows={3} /></Field>

            <div>
              <Label className="overline">Link Media Sosial</Label>
              <div className="space-y-2 mt-1.5">
                {form.medsos.map((m, i) => (
                  <div key={i} className="flex gap-2">
                    <Input data-testid={`kontra-medsos-${i}`} value={m} onChange={(e) => setMedsos(i, e.target.value)} placeholder="https://..." className="bg-zinc-950 border-zinc-800 rounded-sm flex-1" />
                    <Button type="button" onClick={() => rmMedsos(i)} className="bg-zinc-900 hover:bg-red-900 border border-zinc-800 h-9 px-3"><Trash size={12} /></Button>
                  </div>
                ))}
                <Button type="button" onClick={addMedsos} data-testid="kontra-add-medsos" className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 btn-tactical h-8 rounded-sm">
                  <Plus size={12} weight="bold" className="mr-1" /> Tambah Link
                </Button>
              </div>
            </div>

            <ImageUploader label="Gambar SNA" value={form.sna_image} onChange={(v) => set("sna_image", v)} testid="kontra-sna" />
            <ImageUploader label="Gambar Lainnya" value={form.lainnya_image} onChange={(v) => set("lainnya_image", v)} testid="kontra-lainnya" />
            <Field label="Keterangan"><Textarea data-testid="kontra-ket" value={form.keterangan} onChange={(e) => set("keterangan", e.target.value)} className={INP} rows={2} /></Field>

            <div className="flex gap-2">
              <Button type="submit" disabled={busy} data-testid="kontra-submit" className="flex-1 bg-amber-500 hover:bg-amber-400 text-zinc-950 btn-tactical rounded-sm h-10">
                {busy ? "Menyimpan..." : (editId ? "Perbarui Profiling" : "Simpan Profiling")}
              </Button>
              {editId && (
                <Button type="button" onClick={cancelEdit} data-testid="kontra-cancel-edit" className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 btn-tactical rounded-sm h-10 px-4">
                  <X size={14} weight="bold" className="mr-1" /> Batal
                </Button>
              )}
            </div>
          </form>
        </Card>

        <Card title="Daftar Laporan Hari Ini" kicker={`PERIODE ${periodLabel}`} testid="kontra-list-card">
          {items.length === 0 ? <Empty /> : (
            <ul className="space-y-3">
              {items.map((it) => (
                <li key={it.id} className={`bg-zinc-950 border rounded-sm p-3 ${editId === it.id ? "border-amber-500/50" : "border-zinc-800"}`} data-testid={`kontra-item-${it.id}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-bold text-sm">{it.nama_to}</p>
                        <span className={`text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm ${it.sumber === "to_satgas" ? "bg-red-500/15 text-red-400" : "bg-blue-500/15 text-blue-400"}`}>{it.sumber?.replace("_", " ")}</span>
                        <span className="text-[9px] font-mono uppercase tracking-wider text-zinc-500">{it.tipe}</span>
                      </div>
                      <p className="text-xs text-zinc-400 mt-1 line-clamp-2">{it.data_diri}</p>
                      {it.keterangan && <p className="text-[11px] text-zinc-500 mt-1 italic">{it.keterangan}</p>}
                    </div>
                    <div className="flex gap-1 items-start">
                      <button onClick={() => startEdit(it)} data-testid={`kontra-edit-${it.id}`} className="text-zinc-500 hover:text-amber-400 p-1" title="Edit"><PencilSimple size={14} weight="bold" /></button>
                      <button onClick={() => del(it.id)} data-testid={`kontra-delete-${it.id}`} className="text-zinc-500 hover:text-red-400 p-1" title="Hapus"><Trash size={14} weight="bold" /></button>
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

function Field({ label, children }) { return (<div><Label className="overline">{label}</Label>{children}</div>); }
