import { useState, useRef, useEffect, useMemo } from "react";
import { MagnifyingGlass, X, FileText, Spinner } from "@phosphor-icons/react";
import { api, apiErrorMsg } from "@/lib/api";
import { toast } from "sonner";

const TYPE_BADGE_COLOR = {
  lid: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  kontra: "bg-red-500/15 text-red-400 border-red-500/30",
  gal: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  medmon: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  piket: "bg-zinc-500/15 text-zinc-300 border-zinc-500/30",
  geoint: "bg-fuchsia-500/15 text-fuchsia-400 border-fuchsia-500/30",
};

// Field labels in Indonesian
const FIELD_LABEL = {
  judul: "Judul", fakta: "Fakta", analisa: "Analisa",
  tindakan: "Tindakan Satgas", rekomendasi: "Rekomendasi BAIS",
  link: "Link", cog: "Wilayah COG",
  nama_to: "Nama TO", data_diri: "Data Diri", keterangan: "Keterangan",
  sumber: "Sumber", tipe: "Tipe", medsos: "Medsos",
  kategori: "Kategori", links: "Tautan",
  subjek: "Subjek", ringkasan: "Ringkasan",
  isi: "Isi Laporan", satgas: "Satgas",
  nama_orang: "Nama", wilayah: "Wilayah", status: "Status",
};

// Highlight matches inside a string by wrapping in <mark>
function highlightText(text, query) {
  if (!text || !query) return text || "";
  try {
    const safe = String(query).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const parts = String(text).split(new RegExp(`(${safe})`, "gi"));
    return parts.map((p, i) =>
      p.toLowerCase() === String(query).toLowerCase() ? (
        <mark
          key={i}
          className="bg-yellow-400/90 text-zinc-900 rounded-sm px-0.5"
          data-match="hit"
        >
          {p}
        </mark>
      ) : (
        <span key={i}>{p}</span>
      )
    );
  } catch {
    return text;
  }
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [openItem, setOpenItem] = useState(null);
  const inputRef = useRef(null);

  // Debounce
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(query.trim()), 350);
    return () => clearTimeout(t);
  }, [query]);

  // Fetch
  useEffect(() => {
    if (debouncedQ.length < 2) {
      setResults([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const { data } = await api.get("/search", {
          params: { q: debouncedQ, limit: 50 },
        });
        if (!cancelled) setResults(data.results || []);
      } catch (e) {
        if (!cancelled) {
          toast.error(apiErrorMsg(e, "Gagal mencari"));
          setResults([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [debouncedQ]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <div className="space-y-6" data-testid="search-page">
      <header className="flex items-center justify-between border-b border-zinc-800 pb-4">
        <div>
          <p className="overline text-amber-500">Pencarian</p>
          <h1 className="text-3xl font-black uppercase tracking-tighter mt-1">
            Cari Laporan
          </h1>
          <p className="text-xs text-zinc-500 mt-1">
            Pencarian teks pada semua laporan tim (LID, KONTRA, GAL, MEDMON, GEOINT, PIKET).
          </p>
        </div>
      </header>

      {/* Search input */}
      <div className="relative max-w-3xl">
        <MagnifyingGlass
          size={18}
          weight="bold"
          className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"
        />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ketik kata kunci... minimal 2 karakter"
          data-testid="search-input"
          className="w-full bg-zinc-950 border border-zinc-800 focus:border-amber-500/60 focus:outline-none rounded-sm pl-10 pr-10 py-3 text-sm placeholder-zinc-600"
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery("")}
            data-testid="search-clear"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-200"
            title="Bersihkan"
          >
            <X size={16} weight="bold" />
          </button>
        )}
      </div>

      {/* Status bar */}
      <div className="flex items-center gap-3 text-xs text-zinc-500" data-testid="search-status">
        {loading && (
          <>
            <Spinner size={14} className="animate-spin" />
            <span>Mencari...</span>
          </>
        )}
        {!loading && debouncedQ.length >= 2 && (
          <span>
            <span className="font-mono text-amber-400" data-testid="search-result-count">
              {results.length}
            </span>{" "}
            hasil untuk{" "}
            <span className="font-mono text-zinc-200">"{debouncedQ}"</span>
          </span>
        )}
        {!loading && debouncedQ.length < 2 && (
          <span>Mulai mengetik untuk mencari laporan...</span>
        )}
      </div>

      {/* Results */}
      <ul className="space-y-3" data-testid="search-results">
        {results.map((r) => (
          <li key={`${r.type}-${r.id}`} data-testid={`search-result-${r.type}-${r.id}`}>
            <button
              type="button"
              onClick={() => setOpenItem(r)}
              className="w-full text-left bg-zinc-950 border border-zinc-800 hover:border-amber-500/40 rounded-sm p-4 transition-colors group"
              data-testid={`search-open-${r.type}-${r.id}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1.5">
                    <span
                      className={`text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 border rounded-sm ${
                        TYPE_BADGE_COLOR[r.type] || "bg-zinc-800 text-zinc-300"
                      }`}
                    >
                      {r.badge}
                    </span>
                    <span className="text-[10px] font-mono text-zinc-500">
                      {r.report_date || "—"}
                    </span>
                  </div>
                  <p className="font-bold text-sm text-zinc-100 group-hover:text-amber-300 line-clamp-2">
                    {highlightText(r.title, debouncedQ)}
                  </p>
                  <div className="mt-2 space-y-1">
                    {r.snippets.slice(0, 3).map((s, i) => (
                      <p key={i} className="text-xs text-zinc-400 line-clamp-2">
                        <span className="text-[9px] font-mono uppercase tracking-wider text-zinc-600 mr-1.5">
                          {FIELD_LABEL[s.field] || s.field}
                        </span>
                        {highlightText(s.snippet, debouncedQ)}
                      </p>
                    ))}
                  </div>
                </div>
                <FileText size={20} weight="duotone" className="text-zinc-600 shrink-0" />
              </div>
            </button>
          </li>
        ))}
      </ul>

      {/* Preview modal */}
      {openItem && (
        <PreviewModal
          item={openItem}
          query={debouncedQ}
          onClose={() => setOpenItem(null)}
        />
      )}
    </div>
  );
}

function PreviewModal({ item, query, onClose }) {
  const contentRef = useRef(null);

  // Scroll to first mark on open
  useEffect(() => {
    const t = setTimeout(() => {
      const firstMark = contentRef.current?.querySelector('[data-match="hit"]');
      if (firstMark) {
        firstMark.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 200);
    return () => clearTimeout(t);
  }, [item]);

  // ESC closes
  useEffect(() => {
    const h = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);

  const renderedFields = useMemo(
    () => buildFieldOrder(item.type, item.full_doc),
    [item]
  );
  const matchCount = useMemo(() => {
    if (!query) return 0;
    let count = 0;
    const rx = new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
    for (const { value } of renderedFields) {
      if (typeof value === "string") {
        count += (value.match(rx) || []).length;
      } else if (Array.isArray(value)) {
        count += value.reduce((a, v) => a + ((String(v).match(rx) || []).length), 0);
      }
    }
    return count;
  }, [renderedFields, query]);

  return (
    <div
      className="fixed inset-0 z-50 bg-zinc-950/85 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6 md:p-10"
      onClick={onClose}
      data-testid="search-preview-modal"
    >
      <div
        className="w-full max-w-4xl max-h-[92vh] bg-zinc-950 border border-zinc-800 rounded-sm flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between gap-3 border-b border-zinc-800 px-5 py-3">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <span
              className={`text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 border rounded-sm shrink-0 ${
                TYPE_BADGE_COLOR[item.type] || "bg-zinc-800 text-zinc-300"
              }`}
            >
              {item.badge}
            </span>
            <p className="font-bold text-sm truncate">{item.title}</p>
            <span className="text-[10px] font-mono text-zinc-500 shrink-0">
              {item.report_date}
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span
              className="text-[10px] font-mono uppercase tracking-wider text-yellow-400"
              data-testid="search-preview-match-count"
            >
              {matchCount} kecocokan
            </span>
            <button
              type="button"
              onClick={onClose}
              data-testid="search-preview-close"
              className="p-1.5 hover:bg-zinc-900 rounded-sm transition-colors"
              title="Tutup (ESC)"
            >
              <X size={16} weight="bold" />
            </button>
          </div>
        </header>

        <div ref={contentRef} className="overflow-y-auto p-5 space-y-4 flex-1" data-testid="search-preview-content">
          {renderedFields.map(({ key, label, value, kind }) => (
            <FieldRow
              key={key}
              label={label}
              value={value}
              kind={kind}
              query={query}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function FieldRow({ label, value, kind, query }) {
  if (value === undefined || value === null || value === "") return null;
  if (Array.isArray(value) && value.length === 0) return null;
  return (
    <div className="border-b border-zinc-900/60 last:border-0 pb-3">
      <p className="overline text-zinc-500 mb-1.5">{label}</p>
      {Array.isArray(value) ? (
        <ul className="space-y-1">
          {value.map((v, i) => (
            <li key={i} className="text-xs text-zinc-200 font-mono break-all">
              {kind === "link" ? (
                <a
                  href={String(v)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-amber-400 hover:underline"
                >
                  {highlightText(String(v), query)}
                </a>
              ) : (
                highlightText(String(v), query)
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p
          className={`whitespace-pre-wrap text-sm text-zinc-200 leading-relaxed ${
            kind === "title" ? "font-bold text-base" : ""
          }`}
        >
          {highlightText(String(value), query)}
        </p>
      )}
    </div>
  );
}

// Per-type ordered field list for the preview modal
function buildFieldOrder(type, doc) {
  if (!doc) return [];
  const orders = {
    lid: [
      ["judul", "Judul", "title"],
      ["cog", "Wilayah COG"],
      ["link", "Link", "link"],
      ["fakta", "Fakta"],
      ["analisa", "Analisa"],
      ["tindakan", "Tindakan Satgas"],
      ["rekomendasi", "Rekomendasi BAIS"],
    ],
    kontra: [
      ["nama_to", "Nama TO", "title"],
      ["tipe", "Tipe"],
      ["sumber", "Sumber"],
      ["data_diri", "Data Diri"],
      ["medsos", "Medsos", "link"],
      ["keterangan", "Keterangan"],
    ],
    gal: [
      ["judul", "Judul", "title"],
      ["kategori", "Kategori"],
      ["links", "Tautan Konten", "link"],
      ["keterangan", "Keterangan"],
    ],
    medmon: [
      ["subjek", "Subjek", "title"],
      ["ringkasan", "Ringkasan"],
      ["analisa", "Analisa"],
      ["rekomendasi", "Rekomendasi"],
      ["sentiment_positif", "Sentiment Positif (%)"],
      ["sentiment_negatif", "Sentiment Negatif (%)"],
      ["sentiment_netral", "Sentiment Netral (%)"],
    ],
    piket: [
      ["judul", "Judul", "title"],
      ["satgas", "Satgas"],
      ["isi", "Isi Laporan"],
    ],
    geoint: [
      ["nama_orang", "Nama", "title"],
      ["wilayah", "Wilayah"],
      ["status", "Status"],
      ["lat", "Latitude"],
      ["lon", "Longitude"],
    ],
  };
  const tpl = orders[type] || Object.keys(doc).map((k) => [k, k]);
  return tpl
    .map(([k, label, kind]) => ({ key: k, label, value: doc[k], kind }))
    .filter((f) => f.value !== undefined && f.value !== null && f.value !== "");
}
