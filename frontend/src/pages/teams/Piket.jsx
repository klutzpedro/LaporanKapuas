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
import { Trash, PencilSimple, X } from "@phosphor-icons/react";

const INP = "bg-zinc-950 border-zinc-800 rounded-sm focus-visible:ring-amber-500/40 focus-visible:border-amber-500 mt-1.5";
const EMPTY = { satgas: "tek", judul: "", isi: "", gambar: null };
const SATGAS = { tek: "SATGAS TEK", sandi: "SATGAS SANDI", medis: "SATGAS MEDIS" };

export default function Piket() {
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState(null);
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const { reportDate, periodLabel } = usePeriod();

  async function load() {
    const params = reportDate ? { report_date: reportDate, fallback_previous: true } : {};
    const { data } = await api.get("/piket", { params });
    setItems(data);
  }
  useEffect(() => { load(); }, [reportDate]);
  function set(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  function startEdit(it) {
    setEditId(it.id);
    setForm({
      satgas: it.satgas || "tek",
      judul: it.judul || "",
      isi: it.isi || "",
      gambar: it.gambar || null,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function cancelEdit() { setEditId(null); setForm(EMPTY); }

  async function submit(e) {
    e.preventDefault(); setBusy(true);
    try {
      if (editId) {
        await api.put(`/piket/${editId}`, form);
        toast.success("Laporan piket diperbarui.");
      } else {
        await api.post("/piket", form);
        toast.success("Laporan piket tersimpan.");
      }
      setForm(EMPTY); setEditId(null); load();
    } catch (e2) { toast.error(apiErrorMsg(e2, "Gagal menyimpan.")); }
    finally { setBusy(false); }
  }

  async function del(id) {
    if (!confirm("Hapus?")) return;
    await api.delete(`/piket/${id}`);
    if (editId === id) cancelEdit();
    load();
  }

  return (
    <div data-testid="piket-page">
      <PageHeader overline="PIKET" title="Laporan Satgas TEK/SANDI/MEDIS" subtitle="Konsolidasi data dari Satgas oleh Piket" />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title={editId ? "Edit Piket" : "Form Piket"} color={editId ? "#10B981" : "#A1A1AA"} testid="piket-form-card">
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

            <div className="flex gap-2">
              <Button type="submit" disabled={busy} data-testid="piket-submit" className="flex-1 bg-amber-500 hover:bg-amber-400 text-zinc-950 btn-tactical rounded-sm h-10">
                {busy ? "Menyimpan..." : (editId ? "Perbarui Laporan" : "Simpan Laporan")}
              </Button>
              {editId && (
                <Button type="button" onClick={cancelEdit} data-testid="piket-cancel-edit" className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 btn-tactical rounded-sm h-10 px-4">
                  <X size={14} weight="bold" className="mr-1" /> Batal
                </Button>
              )}
            </div>
          </form>
        </Card>

        <Card title="Daftar Laporan Hari Ini" kicker={`PERIODE ${periodLabel}`} testid="piket-list-card">
          <PreviousPeriodBanner items={items} currentDate={reportDate} />
          {items.length === 0 ? <Empty /> : (
            <ul className="space-y-3">
              {items.map((it) => (
                <li key={it.id} className={`bg-zinc-950 border rounded-sm p-3 ${editId === it.id ? "border-amber-500/50" : "border-zinc-800"}`} data-testid={`piket-item-${it.id}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm bg-zinc-800 text-zinc-300">{SATGAS[it.satgas]}</span>
                      <p className="font-bold text-sm mt-1">{it.judul}</p>
                      <p className="text-xs text-zinc-400 mt-1 line-clamp-3">{it.isi}</p>
                    </div>
                    <div className="flex gap-1 items-start">
                      <button onClick={() => startEdit(it)} data-testid={`piket-edit-${it.id}`} className="text-zinc-500 hover:text-amber-400 p-1" title="Edit"><PencilSimple size={14} weight="bold" /></button>
                      <button onClick={() => del(it.id)} data-testid={`piket-delete-${it.id}`} className="text-zinc-500 hover:text-red-400 p-1" title="Hapus"><Trash size={14} weight="bold" /></button>
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
