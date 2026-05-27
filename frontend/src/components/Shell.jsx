export function PageHeader({ overline, title, subtitle, right, testid }) {
  return (
    <div className="border-b border-zinc-800 bg-zinc-950 px-6 py-5 flex items-end justify-between gap-4" data-testid={testid}>
      <div>
        {overline && <p className="overline mb-1">{overline}</p>}
        <h1 className="text-2xl md:text-3xl font-black uppercase tracking-tighter leading-none">{title}</h1>
        {subtitle && <p className="text-xs text-zinc-500 mt-2 font-mono">{subtitle}</p>}
      </div>
      {right && <div className="flex items-center gap-2">{right}</div>}
    </div>
  );
}

export function Card({ title, kicker, color, right, children, testid, className = "" }) {
  return (
    <div className={`bg-zinc-900 border border-zinc-800 rounded-sm ${className}`} data-testid={testid}>
      {(title || right) && (
        <div className="flex items-center justify-between gap-2 px-4 py-3 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            {color && <span className="w-1 h-4 rounded-sm" style={{ background: color }} />}
            <div>
              {kicker && <p className="overline text-[9px]">{kicker}</p>}
              {title && <h3 className="text-sm font-bold uppercase tracking-wide">{title}</h3>}
            </div>
          </div>
          {right}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}

export function StatTile({ label, value, color = "#F59E0B", testid }) {
  return (
    <div
      className="bg-zinc-900 border border-zinc-800 rounded-sm px-4 py-3 flex flex-col justify-between min-h-[110px]"
      data-testid={testid}
    >
      <p className="overline whitespace-nowrap truncate">{label}</p>
      <p
        className="text-4xl font-black tracking-tighter leading-none tabular-nums"
        style={{ color }}
        data-testid={`${testid}-value`}
      >
        {value}
      </p>
    </div>
  );
}

export function Empty({ text = "Tidak ada data" }) {
  return <div className="text-xs italic text-zinc-500 px-2 py-4 text-center">{text}</div>;
}
