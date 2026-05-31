import { Label } from "./ui/label";
import { Input } from "./ui/input";

/**
 * SentimentInput
 * 3 number inputs (positif, negatif, netral) + live SVG pie preview.
 * Values are percentages, support decimals (e.g. 44.38 or 44,38).
 */
export function SentimentInput({ value, onChange, testid = "sentiment" }) {
  const pos = clamp(toNum(value?.positif));
  const neg = clamp(toNum(value?.negatif));
  const net = clamp(toNum(value?.netral));
  const total = round2(pos + neg + net);
  const ok = Math.abs(total - 100) < 0.01;

  function set(k, v) {
    onChange({ ...value, [k]: clamp(toNum(v)) });
  }

  return (
    <div data-testid={`${testid}-input`}>
      <Label className="overline">Sentiment Publik (Total Harus 100%)</Label>
      <div className="grid grid-cols-[1fr_120px] gap-4 mt-1.5">
        <div className="space-y-2">
          <Row color="#10B981" label="Positif" value={pos} onChange={(v) => set("positif", v)} testid={`${testid}-positif`} />
          <Row color="#EF4444" label="Negatif" value={neg} onChange={(v) => set("negatif", v)} testid={`${testid}-negatif`} />
          <Row color="#A1A1AA" label="Netral" value={net} onChange={(v) => set("netral", v)} testid={`${testid}-netral`} />
          <div className={`text-[11px] font-mono mt-1 ${ok ? "text-emerald-400" : "text-red-400"}`} data-testid={`${testid}-total`}>
            Total: {formatNum(total)}% {ok ? "✓" : "(harus = 100%)"}
          </div>
        </div>
        <SentimentPie positif={pos} negatif={neg} netral={net} size={108} />
      </div>
    </div>
  );
}

function Row({ color, label, value, onChange, testid }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-3 h-3 rounded-sm shrink-0" style={{ background: color }} />
      <span className="text-xs font-mono uppercase tracking-wider text-zinc-400 w-16">{label}</span>
      <Input
        type="text"
        inputMode="decimal"
        value={value === 0 ? "" : formatNum(value)}
        placeholder="0"
        onChange={(e) => onChange(e.target.value)}
        onFocus={(e) => e.target.select()}
        data-testid={testid}
        className="bg-zinc-950 border-zinc-800 rounded-sm h-8 w-24 font-mono text-sm"
      />
      <span className="text-xs text-zinc-500">%</span>
    </div>
  );
}

export function SentimentPie({ positif = 0, negatif = 0, netral = 0, size = 96 }) {
  const total = positif + negatif + netral;
  const segments = total > 0
    ? [
        { value: positif, color: "#10B981" },
        { value: negatif, color: "#EF4444" },
        { value: netral, color: "#A1A1AA" },
      ].filter((s) => s.value > 0)
    : [{ value: 1, color: "#27272A" }];

  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 2;
  let angleStart = -Math.PI / 2;
  const paths = segments.map((s, i) => {
    const angle = (s.value / Math.max(0.0001, total)) * 2 * Math.PI;
    const x1 = cx + r * Math.cos(angleStart);
    const y1 = cy + r * Math.sin(angleStart);
    const x2 = cx + r * Math.cos(angleStart + angle);
    const y2 = cy + r * Math.sin(angleStart + angle);
    const largeArc = angle > Math.PI ? 1 : 0;
    let d;
    if (segments.length === 1 && total > 0 && s.value === total) {
      d = `M ${cx},${cy - r} A ${r},${r} 0 1 1 ${cx - 0.01},${cy - r} Z`;
    } else {
      d = `M ${cx},${cy} L ${x1},${y1} A ${r},${r} 0 ${largeArc} 1 ${x2},${y2} Z`;
    }
    angleStart += angle;
    return <path key={i} d={d} fill={s.color} stroke="#0A0A0A" strokeWidth="1" />;
  });

  return (
    <svg width={size} height={size} className="block" data-testid="sentiment-pie-preview">
      {paths}
      <circle cx={cx} cy={cy} r={r * 0.55} fill="#0A0A0A" />
      <text x={cx} y={cy + 2} textAnchor="middle" fill="#F59E0B" fontSize="11" fontWeight="bold" fontFamily="ui-monospace, monospace">
        {formatNum(total)}%
      </text>
    </svg>
  );
}

// ---------- helpers ----------
function toNum(v) {
  if (v === null || v === undefined || v === "") return 0;
  // Accept both comma and dot as decimal separator (Indonesian users use comma)
  const s = String(v).replace(",", ".").trim();
  if (s === "") return 0;
  const n = parseFloat(s);
  return Number.isNaN(n) ? 0 : n;
}

function clamp(n) {
  if (Number.isNaN(n)) return 0;
  return Math.max(0, Math.min(100, n));
}

function round2(n) {
  return Math.round(n * 100) / 100;
}

function formatNum(n) {
  // Show integer if whole number, otherwise up to 2 decimals
  if (n === 0) return "0";
  const r = round2(n);
  if (Number.isInteger(r)) return String(r);
  return String(r).replace(".", ",");
}
