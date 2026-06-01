import { useEffect, useState } from "react";
import { api, COG_LABEL, COG_COLOR } from "@/lib/api";
import { PageHeader, Card, StatTile, Empty } from "@/components/Shell";
import { Newspaper, UserFocus, Megaphone, ChartLineUp, Crosshair, ClipboardText, ArrowsClockwise } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";

const TEAMS = [
  { key: "lid", label: "TIM LID", icon: Newspaper, color: "#F59E0B" },
  { key: "kontra", label: "KONTRA", icon: UserFocus, color: "#EF4444" },
  { key: "gal", label: "TIM GAL", icon: Megaphone, color: "#3B82F6" },
  { key: "medmon", label: "MEDMON", icon: ChartLineUp, color: "#8B5CF6" },
  { key: "geoint", label: "GEOINT", icon: Crosshair, color: "#10B981" },
  { key: "piket", label: "PIKET", icon: ClipboardText, color: "#A1A1AA" },
];

export default function Dashboard() {
  const [info, setInfo] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [i, d] = await Promise.all([api.get("/daily/info"), api.get("/daily")]);
      setInfo(i.data);
      setData(d.data);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  const counts = {};
  TEAMS.forEach((t) => { counts[t.key] = data?.[t.key]?.length || 0; });

  const lidByCog = { aceh: [], jakarta: [], indonesia: [], papua: [], internasional: [] };
  (data?.lid || []).forEach((it) => { if (lidByCog[it.cog]) lidByCog[it.cog].push(it); });

  return (
    <div data-testid="dashboard-page">
      <PageHeader
        overline="OPERATIONS // RINGKASAN HARIAN"
        title="Control Room"
        subtitle={
          info
            ? `Tanggal laporan aktif: ${info.report_date} • ${(info.before_cutoff ?? info.before_noon) ? `Sebelum ${String(info.cutoff_hour ?? 9).padStart(2,"0")}:${String(info.cutoff_minute ?? 0).padStart(2,"0")} WIB (menampilkan H-1)` : `Setelah ${String(info.cutoff_hour ?? 9).padStart(2,"0")}:${String(info.cutoff_minute ?? 0).padStart(2,"0")} WIB (hari ini)`}`
            : ""
        }
        right={
          <Button
            onClick={load}
            disabled={loading}
            data-testid="dashboard-refresh"
            className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-100 btn-tactical rounded-sm h-9"
          >
            <ArrowsClockwise size={14} weight="bold" className="mr-2" />
            Refresh
          </Button>
        }
        testid="dashboard-header"
      />

      <div className="p-6 space-y-6">
        {/* KPI strip */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {TEAMS.map((t) => (
            <StatTile
              key={t.key}
              label={t.label}
              value={counts[t.key]}
              color={t.color}
              testid={`stat-${t.key}`}
            />
          ))}
        </div>

        {/* 4 COG panels */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.keys(lidByCog).map((cog) => (
            <Card
              key={cog}
              title={`COG ${COG_LABEL[cog]}`}
              kicker={`${lidByCog[cog].length} item`}
              color={COG_COLOR[cog]}
              testid={`cog-card-${cog}`}
            >
              {lidByCog[cog].length === 0 ? (
                <Empty text="Belum ada laporan LID untuk COG ini." />
              ) : (
                <ul className="space-y-3">
                  {lidByCog[cog].map((it) => (
                    <li key={it.id} className="border-l-2 pl-3" style={{ borderColor: COG_COLOR[cog] }}>
                      <p className="text-sm font-bold text-zinc-100 leading-snug">{it.judul}</p>
                      {it.link && (
                        <a href={it.link} target="_blank" rel="noreferrer" className="text-[11px] font-mono text-amber-400 hover:underline break-all">
                          {it.link}
                        </a>
                      )}
                      {it.analisa && (
                        <p className="text-xs text-zinc-400 mt-1.5 leading-relaxed line-clamp-3">{it.analisa}</p>
                      )}
                      <div className="flex items-center gap-3 mt-1.5 text-[10px] font-mono text-zinc-500">
                        <span>OLEH: {it.created_by_name || "-"}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          ))}
        </div>

        {/* Quick views */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card title="Profiling Kontra (Top 5)" color="#EF4444" testid="card-kontra">
            {(data?.kontra || []).length === 0 ? <Empty /> : (
              <ul className="space-y-2 text-sm">
                {(data?.kontra || []).slice(0, 5).map((it) => (
                  <li key={it.id} className="flex items-start justify-between gap-3 border-b border-zinc-800 pb-2">
                    <div>
                      <p className="font-bold">{it.nama_to}</p>
                      <p className="text-xs text-zinc-400 line-clamp-2">{it.data_diri}</p>
                    </div>
                    <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-sm shrink-0 ${
                      it.sumber === "to_satgas" ? "bg-red-500/10 text-red-400" : "bg-blue-500/10 text-blue-400"
                    }`}>
                      {it.sumber?.replace("_", " ")}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Posisi OPM Termonitor" color="#10B981" testid="card-geoint">
            {(data?.geoint || []).length === 0 ? <Empty /> : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left overline">
                    <th className="pb-2">Wilayah</th>
                    <th className="pb-2">Nama</th>
                    <th className="pb-2">Status</th>
                    <th className="pb-2">Koordinat</th>
                  </tr>
                </thead>
                <tbody className="font-mono">
                  {(data?.geoint || []).slice(0, 6).map((it) => (
                    <tr key={it.id} className="border-t border-zinc-800">
                      <td className="py-1.5">{it.wilayah}</td>
                      <td className="py-1.5">{it.nama_orang}</td>
                      <td className={it.status === "aktif" ? "text-red-400" : "text-emerald-400"}>{it.status?.toUpperCase()}</td>
                      <td className="text-zinc-400">{it.lat}, {it.lon}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
