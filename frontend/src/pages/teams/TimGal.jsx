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
import { Plus, Trash, PencilSimple, X, ChartBar } from "@phosphor-icons/react";

const INP = "bg-zinc-950 border-zinc-800 rounded-sm focus-visible:ring-amber-500/40 focus-visible:border-amber-500 mt-1.5";
const EMPTY = { kategori: "narasi", judul: "", gambar: null, links: [""], keterangan: "" };
const CATEGORY = { narasi: "NARASI", video: "VIDEO", meme: "MEME" };

// 5 platform sosmed yang dipantau Tim GAL
const PLATFORMS = [
  { key: "instagram", label: "Instagram", color: "#E1306C" },
  { key: "facebook",  label: "Facebook",  color: "#1877F2" },
  { key: "twitter",   label: "Twitter/X", color: "#1DA1F2" },
  { key: "tiktok",    label: "TikTok",    color: "#69C9D0" },
  { key: "youtube",   label: "YouTube",   color: "#FF0000" },
];

const KATEGORIES = ["narasi", "video", "meme"];

function emptyStats() {
  const obj = {};
  for (const c of KATEGORIES) {
    obj[c] = {};
    for (const p of PLATFORMS) obj[c][p.key] = 0;
  }
  return obj;
}

function normalizeKategori(k) {
  return k === "medsos" ? "meme" : (k || "narasi");
}

export default function TimGal() {
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState(null);
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);

  // Stats state — counts of penggalangan per kategori per platform
  const [stats, setStats] = useState(emptyStats());
  const [statsBusy, setStatsBusy] = useState(false);
  const [statsUpdatedAt, setStatsUpdatedAt] = useState(null);

  const { reportDate, periodLabel } = usePeriod();

  async function load() {
    const params = reportDate ? { report_date: reportDate, fallback_previous: true } : {};
    const { data } = await api.get("/gal", { params });
    setItems(data);
  }
  async function loadStats() {
    const params = reportDate ? { report_date: reportDate, fallback_previous: true } : {};
    const { data } = await api.get("/gal/stats", { params });
    const fresh = emptyStats();
    for (const c of KATEGORIES) {
      for (const p of PLATFORMS) {
        fresh[c][p.key] = Number(data?.counts?.[c]?.[p.key] || 0);
      }
    }
    setStats(fresh);
    setStatsUpdatedAt(data?.updated_at || null);
  }
  useEffect(() => { load(); loadStats(); }, [reportDate]);

  function set(k, v) { setForm((f) => ({ ...f, [k]: v })); }
  function setLink(i, v) { setForm((f) => { const a = [...f.links]; a[i] = v; return { ...f, links: a }; }); }
  function setStat(cat, plat, v) {
    const n = Math.max(0, parseInt(v || "0", 10) || 0);
    setStats((s) => ({ ...s, [cat]: { ...s[cat], [plat]: n } }));
  }

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

  async function saveStats() {
    setStatsBusy(true);
    try {
      const payload = { counts: stats, report_date: reportDate };
      const { data } = await api.post("/gal/stats", payload);
      setStatsUpdatedAt(data?.updated_at || null);
      toast.success("Statistik penggalangan tersimpan.");
    } catch (e) {
      toast.error(apiErrorMsg(e, "Gagal menyimpan statistik."));
    } finally { setStatsBusy(false); }
  }

  async function del(id) {
    if (!confirm("Hapus?")) return;
    await api.delete(`/gal/${id}`);
    if (editId === id) cancelEdit();
    load();
  }

  // Computed totals for chart preview
  const totalsPerPlatform = PLATFORMS.map((p) => ({
    ...p,
    total: KATEGORIES.reduce((s, c) => s + (stats[c]?.[p.key] || 0), 0),
    by_cat: KATEGORIES.reduce((acc, c) => ({ ...acc, [c]: stats[c]?.[p.key] || 0 }), {}),
  }));
  const grandTotal = totalsPerPlatform.reduce((s, p) => s + p.total, 0);
  const maxPlatform = Math.max(1, ...totalsPerPlatform.map((p) => p.total));

  return (
    <div data-testid="gal-page">
      <PageHeader overline="TIM GAL" title="Konten Penggalangan" subtitle="Narasi · Video · Meme + Statistik Platform" />
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

      {/* ====== Statistik Penggalangan per Platform ====== */}
      <div className="px-6 pb-6">
        <Card
          title="Statistik Penggalangan per Platform"
          kicker={`TOTAL ${grandTotal} POST` + (statsUpdatedAt ? ` · UPDATE ${new Date(statsUpdatedAt).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}` : "")}
          color="#F59E0B"
          testid="gal-stats-card"
        >
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* ---- Input grid (3 kategori × 5 platform) ---- */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs" data-testid="gal-stats-table">
                <thead>
                  <tr className="text-zinc-500 font-mono uppercase tracking-wider">
                    <th className="text-left py-2 px-2">Kategori</th>
                    {PLATFORMS.map((p) => (
                      <th key={p.key} className="text-center py-2 px-1" style={{ color: p.color }}>{p.label}</th>
                    ))}
                    <th className="text-right py-2 px-2 text-amber-400">∑</th>
                  </tr>
                </thead>
                <tbody>
                  {KATEGORIES.map((cat) => {
                    const rowTotal = PLATFORMS.reduce((s, p) => s + (stats[cat]?.[p.key] || 0), 0);
                    return (
                      <tr key={cat} className="border-t border-zinc-800">
                        <td className="py-1.5 px-2 font-bold text-zinc-200">{CATEGORY[cat]}</td>
                        {PLATFORMS.map((p) => (
                          <td key={p.key} className="py-1 px-1">
                            <Input
                              data-testid={`gal-stat-${cat}-${p.key}`}
                              type="number"
                              min="0"
                              value={stats[cat]?.[p.key] ?? 0}
                              onChange={(e) => setStat(cat, p.key, e.target.value)}
                              onFocus={(e) => e.target.select()}
                              className="bg-zinc-950 border-zinc-800 rounded-sm h-8 w-full font-mono text-center text-sm"
                            />
                          </td>
                        ))}
                        <td className="py-1 px-2 text-right font-mono text-amber-400">{rowTotal}</td>
                      </tr>
                    );
                  })}
                  <tr className="border-t border-zinc-700 bg-zinc-900/50">
                    <td className="py-2 px-2 font-bold text-zinc-400 uppercase text-[10px] font-mono tracking-wider">Total Platform</td>
                    {totalsPerPlatform.map((p) => (
                      <td key={p.key} className="py-2 px-1 text-center font-mono font-bold" style={{ color: p.color }}>{p.total}</td>
                    ))}
                    <td className="py-2 px-2 text-right font-mono font-bold text-amber-400">{grandTotal}</td>
                  </tr>
                </tbody>
              </table>
              <div className="mt-3 flex justify-end">
                <Button onClick={saveStats} disabled={statsBusy} data-testid="gal-stats-submit" className="bg-amber-500 hover:bg-amber-400 text-zinc-950 btn-tactical rounded-sm h-10 px-6">
                  <ChartBar size={14} weight="bold" className="mr-2" />
                  {statsBusy ? "Menyimpan..." : "Simpan Statistik"}
                </Button>
              </div>
            </div>

            {/* ---- Stacked Bar Chart Preview ---- */}
            <div data-testid="gal-stats-chart">
              <Label className="overline">Preview Grafik</Label>
              <div className="mt-3 space-y-3">
                {totalsPerPlatform.map((p) => {
                  const wPct = (p.total / maxPlatform) * 100;
                  const segNarasi = (p.by_cat.narasi / Math.max(1, p.total)) * wPct;
                  const segVideo  = (p.by_cat.video  / Math.max(1, p.total)) * wPct;
                  const segMeme   = (p.by_cat.meme   / Math.max(1, p.total)) * wPct;
                  return (
                    <div key={p.key} className="space-y-1">
                      <div className="flex items-center justify-between text-[11px] font-mono">
                        <span style={{ color: p.color }} className="font-bold uppercase">{p.label}</span>
                        <span className="text-zinc-400">
                          <span className="text-emerald-400">N {p.by_cat.narasi}</span>
                          <span className="mx-1">·</span>
                          <span className="text-blue-400">V {p.by_cat.video}</span>
                          <span className="mx-1">·</span>
                          <span className="text-pink-400">M {p.by_cat.meme}</span>
                          <span className="mx-2 text-amber-400 font-bold">= {p.total}</span>
                        </span>
                      </div>
                      <div className="h-3 bg-zinc-900 rounded-sm overflow-hidden flex">
                        <div className="h-full bg-emerald-500 transition-all" style={{ width: `${segNarasi}%` }} />
                        <div className="h-full bg-blue-500 transition-all" style={{ width: `${segVideo}%` }} />
                        <div className="h-full bg-pink-500 transition-all" style={{ width: `${segMeme}%` }} />
                      </div>
                    </div>
                  );
                })}
                <div className="flex gap-3 text-[10px] font-mono uppercase tracking-wider mt-4 pt-3 border-t border-zinc-800">
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-emerald-500 rounded-sm" /> NARASI</span>
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-blue-500 rounded-sm" /> VIDEO</span>
                  <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 bg-pink-500 rounded-sm" /> MEME</span>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

function Field({ label, children }) { return (<div><Label className="overline">{label}</Label>{children}</div>); }
