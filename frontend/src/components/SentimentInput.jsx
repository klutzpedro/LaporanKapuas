import { Label } from "./ui/label";
import { Input } from "./ui/input";

/**
 * SentimentInput
 * 3 number inputs (positif, negatif, netral) + a live SVG pie preview.
 * Values are percentages. Total displayed for validation feedback.
 */
export function SentimentInput({ value, onChange, testid = "sentiment" }) {
  const pos = clamp(Number(value?.positif) || 0);
  const neg = clamp(Number(value?.negatif) || 0);
  const net = clamp(Number(value?.netral) || 0);
  const total = pos + neg + net;
  const ok = total === 100;

  function set(k, v) {
    onChange({ ...value, [k]: clamp(Number(v) || 0) });
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
            Total: {total}% {ok ? "✓" : "(harus = 100%)"}
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
        type="number"
        inputMode="numeric"
        min={0}
        max={100}
        value={value === 0 ? "" : value}
        placeholder="0"
        onChange={(e) => {
          const v = e.target.value;
          if (v === "") { onChange(0); return; }
          const n = parseInt(v, 10);
          if (Number.isNaN(n)) return;
          onChange(clamp(n));
        }}
        onFocus={(e) => e.target.select()}
        data-testid={testid}
        className="bg-zinc-950 border-zinc-800 rounded-sm h-8 w-20 font-mono text-sm"
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
    const angle = (s.value / Math.max(1, total)) * 2 * Math.PI;
    const x1 = cx + r * Math.cos(angleStart);
    const y1 = cy + r * Math.sin(angleStart);
    const x2 = cx + r * Math.cos(angleStart + angle);
    const y2 = cy + r * Math.sin(angleStart + angle);
    const largeArc = angle > Math.PI ? 1 : 0;
    let d;
    if (segments.length === 1 && total > 0 && s.value === total) {
      // full circle
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
        {total}%
      </text>
    </svg>
  );
}

function clamp(n) {
  if (Number.isNaN(n)) return 0;
  return Math.max(0, Math.min(100, n));
}
