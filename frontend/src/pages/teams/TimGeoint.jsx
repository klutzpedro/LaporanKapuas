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
import { Trash, PencilSimple, X } from "@phosphor-icons/react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const INP = "bg-zinc-950 border-zinc-800 rounded-sm focus-visible:ring-amber-500/40 focus-visible:border-amber-500 mt-1.5";

const redIcon = new L.Icon({
  iconUrl: "https://cdn.jsdelivr.net/gh/pointhi/leaflet-color-markers@master/img/marker-icon-2x-red.png",
  shadowUrl: "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41],
});
const greenIcon = new L.Icon({
  iconUrl: "https://cdn.jsdelivr.net/gh/pointhi/leaflet-color-markers@master/img/marker-icon-2x-green.png",
  shadowUrl: "https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34], shadowSize: [41, 41],
});

const EMPTY = {
  wilayah: "", nama_orang: "", no_hp: "", lat: -4.27, lon: 138.08,
  peta_image: null, status: "aktif", keterangan: "",
};

export default function TimGeoint() {
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState(null);
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const { reportDate, periodLabel } = usePeriod();

  async function load() {
    const params = reportDate ? { report_date: reportDate, fallback_previous: true } : {};
    const { data } = await api.get("/geoint", { params });
    setItems(data);
  }
  useEffect(() => { load(); }, [reportDate]);
  function set(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  function startEdit(it) {
    setEditId(it.id);
    setForm({
      wilayah: it.wilayah || "",
      nama_orang: it.nama_orang || "",
      no_hp: it.no_hp || "",
      lat: it.lat ?? -4.27,
      lon: it.lon ?? 138.08,
      peta_image: it.peta_image || null,
      status: it.status || "aktif",
      keterangan: it.keterangan || "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function cancelEdit() { setEditId(null); setForm(EMPTY); }

  async function submit(e) {
    e.preventDefault(); setBusy(true);
    try {
      const payload = { ...form, lat: parseFloat(form.lat), lon: parseFloat(form.lon) };
      if (editId) {
        await api.put(`/geoint/${editId}`, payload);
        toast.success("Posisi OPM diperbarui.");
      } else {
        await api.post("/geoint", payload);
        toast.success("Posisi OPM tersimpan.");
      }
      setForm(EMPTY); setEditId(null); load();
    } catch (e2) { toast.error(apiErrorMsg(e2, "Gagal menyimpan.")); }
    finally { setBusy(false); }
  }

  async function del(id) {
    if (!confirm("Hapus?")) return;
    await api.delete(`/geoint/${id}`);
    if (editId === id) cancelEdit();
    load();
  }

  return (
    <div data-testid="geoint-page">
      <PageHeader overline="TIM GEOINT" title="Posisi OPM Termonitor" subtitle="Wilayah · Nama · HP · Lat/Lon · Status" />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title={editId ? "Edit Posisi" : "Form Posisi"} color={editId ? "#F59E0B" : "#10B981"} testid="geoint-form-card" className="lg:col-span-1">
          <form onSubmit={submit} className="space-y-4" data-testid="geoint-form">
            <Field label="Wilayah"><Input data-testid="geoint-wilayah" value={form.wilayah} onChange={(e) => set("wilayah", e.target.value)} required className={INP} /></Field>
            <Field label="Nama Orang"><Input data-testid="geoint-nama" value={form.nama_orang} onChange={(e) => set("nama_orang", e.target.value)} required className={INP} /></Field>
            <Field label="No HP"><Input data-testid="geoint-hp" value={form.no_hp} onChange={(e) => set("no_hp", e.target.value)} className={INP} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Latitude"><Input data-testid="geoint-lat" type="number" step="0.000001" value={form.lat} onChange={(e) => set("lat", e.target.value)} required className={INP} /></Field>
              <Field label="Longitude"><Input data-testid="geoint-lon" type="number" step="0.000001" value={form.lon} onChange={(e) => set("lon", e.target.value)} required className={INP} /></Field>
            </div>
            <Field label="Status">
              <Select value={form.status} onValueChange={(v) => set("status", v)}>
                <SelectTrigger data-testid="geoint-status" className={INP}><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="aktif">AKTIF</SelectItem>
                  <SelectItem value="tidak_aktif">TIDAK AKTIF</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <ImageUploader label="Gambar Peta" value={form.peta_image} onChange={(v) => set("peta_image", v)} testid="geoint-peta" />
            <Field label="Keterangan"><Textarea data-testid="geoint-ket" value={form.keterangan} onChange={(e) => set("keterangan", e.target.value)} className={INP} rows={2} /></Field>

            <div className="flex gap-2">
              <Button type="submit" disabled={busy} data-testid="geoint-submit" className="flex-1 bg-amber-500 hover:bg-amber-400 text-zinc-950 btn-tactical rounded-sm h-10">
                {busy ? "Menyimpan..." : (editId ? "Perbarui Posisi" : "Simpan Posisi OPM")}
              </Button>
              {editId && (
                <Button type="button" onClick={cancelEdit} data-testid="geoint-cancel-edit" className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 btn-tactical rounded-sm h-10 px-4">
                  <X size={14} weight="bold" className="mr-1" /> Batal
                </Button>
              )}
            </div>
          </form>
        </Card>

        <Card title="Peta Sebaran OPM" kicker={`PERIODE ${periodLabel}`} testid="geoint-map-card" className="lg:col-span-2">
          <div className="h-[420px] border border-zinc-800 rounded-sm overflow-hidden">
            <MapContainer center={[-2.5, 118]} zoom={4} style={{ height: "100%", width: "100%" }}>
              <TileLayer
                url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                attribution='&copy; OpenStreetMap, &copy; CARTO'
              />
              {items.map((it) => (
                <Marker
                  key={it.id}
                  position={[it.lat, it.lon]}
                  icon={it.status === "aktif" ? redIcon : greenIcon}
                >
                  <Popup>
                    <div style={{ minWidth: 180 }}>
                      <b>{it.nama_orang}</b><br />
                      <small>{it.wilayah}</small><br />
                      Status: <b style={{ color: it.status === "aktif" ? "#EF4444" : "#10B981" }}>{it.status?.toUpperCase()}</b><br />
                      {it.keterangan}
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </div>

          <div className="mt-4">
            <h4 className="overline mb-2">Daftar Laporan Hari Ini</h4>
            <PreviousPeriodBanner items={items} currentDate={reportDate} />
            {items.length === 0 ? <Empty /> : (
              <div className="max-h-[360px] overflow-y-auto pr-1" data-testid="geoint-list-scroll">
                <table className="w-full text-xs">
                  <thead><tr className="overline text-left"><th className="pb-2">Wilayah</th><th className="pb-2">Nama</th><th className="pb-2">Status</th><th className="pb-2">Koordinat</th><th></th></tr></thead>
                  <tbody className="font-mono">
                    {items.map((it) => (
                      <tr key={it.id} className={`border-t border-zinc-800 ${editId === it.id ? "bg-amber-500/5" : ""}`} data-testid={`geoint-item-${it.id}`}>
                        <td className="py-1.5">{it.wilayah}</td>
                        <td className="py-1.5">{it.nama_orang}</td>
                        <td className={it.status === "aktif" ? "text-red-400" : "text-emerald-400"}>{it.status?.toUpperCase()}</td>
                        <td className="text-zinc-400">{it.lat}, {it.lon}</td>
                        <td className="text-right">
                          <ItemActions
                            onEdit={() => startEdit(it)}
                            onDelete={() => del(it.id)}
                            editTestid={`geoint-edit-${it.id}`}
                            deleteTestid={`geoint-delete-${it.id}`}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

function Field({ label, children }) { return (<div><Label className="overline">{label}</Label>{children}</div>); }
