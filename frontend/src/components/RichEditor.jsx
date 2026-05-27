import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import { TextStyle } from "@tiptap/extension-text-style";
import { Color } from "@tiptap/extension-color";
import { FontFamily } from "@tiptap/extension-font-family";
import { Mark, mergeAttributes } from "@tiptap/core";
import { useEffect } from "react";
import {
  TextB, TextItalic, TextUnderline, TextH,
  ListBullets, ListNumbers, ArrowCounterClockwise, ArrowClockwise,
  PaintBucket,
} from "@phosphor-icons/react";

// Custom FontSize mark — applies inline style font-size: <px>
const FontSize = Mark.create({
  name: "fontSize",
  addOptions() { return { types: ["textStyle"] }; },
  addAttributes() {
    return {
      size: {
        default: null,
        parseHTML: (el) => {
          const s = el.style.fontSize;
          if (!s) return null;
          const m = s.match(/(\d+(?:\.\d+)?)/);
          return m ? m[1] : null;
        },
        renderHTML: (attr) => (attr.size ? { style: `font-size: ${attr.size}px` } : {}),
      },
    };
  },
  parseHTML() {
    return [{ tag: "span", getAttrs: (el) => (el.style.fontSize ? null : false) }];
  },
  renderHTML({ HTMLAttributes }) {
    return ["span", mergeAttributes(HTMLAttributes), 0];
  },
  addCommands() {
    return {
      setFontSize:
        (size) =>
        ({ chain }) =>
          chain().setMark("fontSize", { size }).run(),
      unsetFontSize:
        () =>
        ({ chain }) =>
          chain().unsetMark("fontSize").run(),
    };
  },
});

const FONTS = [
  { label: "Sans (IBM Plex)", value: "'IBM Plex Sans', sans-serif" },
  { label: "Serif", value: "Georgia, 'Times New Roman', serif" },
  { label: "Mono (IBM Plex)", value: "'IBM Plex Mono', monospace" },
  { label: "Display (Chivo)", value: "'Chivo', sans-serif" },
];
const COLORS = ["#FAFAFA", "#A1A1AA", "#F59E0B", "#EF4444", "#10B981", "#3B82F6", "#8B5CF6"];
const SIZES = [11, 12, 13, 14, 16, 18, 20, 24];

function btnCls(active) {
  return `inline-flex items-center justify-center w-8 h-8 rounded-sm transition-colors ${
    active
      ? "bg-amber-500 text-zinc-950"
      : "bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-zinc-800"
  }`;
}

export default function RichEditor({ value, onChange, placeholder = "Tulis ringkasan di sini...", testid = "rich-editor" }) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] }, codeBlock: false }),
      Underline,
      TextStyle,
      Color,
      FontFamily,
      FontSize,
    ],
    content: value || "",
    editorProps: {
      attributes: {
        class: "tiptap-content prose prose-invert prose-sm max-w-none focus:outline-none min-h-[280px] px-4 py-3 text-zinc-200",
        "data-testid": `${testid}-content`,
      },
    },
    onUpdate: ({ editor }) => onChange?.(editor.getHTML()),
  });

  useEffect(() => {
    if (!editor) return;
    const current = editor.getHTML();
    if (value && value !== current) editor.commands.setContent(value, false);
  }, [value, editor]);

  if (!editor) return null;

  // Fresh chain per call — prevents stale chain accumulation across clicks
  const run = (fn) => () => fn(editor.chain().focus()).run();

  return (
    <div className="border border-zinc-800 rounded-sm bg-zinc-950" data-testid={testid}>
      <div className="flex flex-wrap items-center gap-1 p-2 border-b border-zinc-800 bg-zinc-900/50">
        <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={run((c) => c.toggleBold())} className={btnCls(editor.isActive("bold"))} title="Bold" data-testid={`${testid}-bold`}>
          <TextB size={14} weight="bold" />
        </button>
        <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={run((c) => c.toggleItalic())} className={btnCls(editor.isActive("italic"))} title="Italic" data-testid={`${testid}-italic`}>
          <TextItalic size={14} weight="bold" />
        </button>
        <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={run((c) => c.toggleUnderline())} className={btnCls(editor.isActive("underline"))} title="Underline" data-testid={`${testid}-underline`}>
          <TextUnderline size={14} weight="bold" />
        </button>

        <span className="w-px h-6 bg-zinc-800 mx-1" />

        <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={run((c) => c.toggleHeading({ level: 2 }))} className={btnCls(editor.isActive("heading", { level: 2 }))} title="Heading" data-testid={`${testid}-h2`}>
          <TextH size={14} weight="bold" />
        </button>
        <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={run((c) => c.toggleBulletList())} className={btnCls(editor.isActive("bulletList"))} title="Bullet list" data-testid={`${testid}-ul`}>
          <ListBullets size={14} weight="bold" />
        </button>
        <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={run((c) => c.toggleOrderedList())} className={btnCls(editor.isActive("orderedList"))} title="Numbered list" data-testid={`${testid}-ol`}>
          <ListNumbers size={14} weight="bold" />
        </button>

        <span className="w-px h-6 bg-zinc-800 mx-1" />

        <select
          onMouseDown={(e) => e.stopPropagation()}
          onChange={(e) => {
            const v = e.target.value;
            const c = editor.chain().focus();
            if (v) c.setFontFamily(v).run(); else c.unsetFontFamily().run();
            e.target.value = "";
          }}
          defaultValue=""
          className="bg-zinc-900 border border-zinc-800 text-zinc-200 text-xs h-8 px-2 rounded-sm font-mono"
          title="Font"
          data-testid={`${testid}-font-family`}
        >
          <option value="" disabled>FONT</option>
          {FONTS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
        </select>

        <select
          onMouseDown={(e) => e.stopPropagation()}
          onChange={(e) => {
            const v = e.target.value;
            const c = editor.chain().focus();
            if (v) c.setFontSize(v).run(); else c.unsetFontSize().run();
            e.target.value = "";
          }}
          defaultValue=""
          className="bg-zinc-900 border border-zinc-800 text-zinc-200 text-xs h-8 px-2 rounded-sm font-mono"
          title="Ukuran font"
          data-testid={`${testid}-font-size`}
        >
          <option value="" disabled>UKURAN</option>
          {SIZES.map((s) => <option key={s} value={s}>{s} px</option>)}
        </select>

        <span className="w-px h-6 bg-zinc-800 mx-1" />

        <div className="flex items-center gap-1" title="Warna teks">
          <PaintBucket size={14} className="text-zinc-400" />
          {COLORS.map((col) => (
            <button
              key={col}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={run((c) => c.setColor(col))}
              className="w-5 h-5 rounded-sm border border-zinc-700 hover:scale-110 transition-transform"
              style={{ background: col }}
              title={col}
              data-testid={`${testid}-color-${col.slice(1)}`}
            />
          ))}
          <button
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={run((c) => c.unsetColor())}
            className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 hover:text-zinc-300 ml-1 px-1.5 h-5 border border-zinc-800 rounded-sm"
            data-testid={`${testid}-color-reset`}
          >
            reset
          </button>
        </div>

        <span className="flex-1" />

        <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={run((c) => c.undo())} className={btnCls(false)} title="Undo" data-testid={`${testid}-undo`}>
          <ArrowCounterClockwise size={14} weight="bold" />
        </button>
        <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={run((c) => c.redo())} className={btnCls(false)} title="Redo" data-testid={`${testid}-redo`}>
          <ArrowClockwise size={14} weight="bold" />
        </button>
      </div>

      <div className="overflow-y-auto max-h-[60vh]">
        <EditorContent editor={editor} placeholder={placeholder} />
      </div>

      <style>{`
        .tiptap-content h1, .tiptap-content h2, .tiptap-content h3 {
          font-family: 'Chivo', sans-serif; font-weight: 800;
          letter-spacing: -0.01em; color: #FAFAFA; margin: 0.8rem 0 0.4rem;
        }
        .tiptap-content h1 { font-size: 1.4rem; }
        .tiptap-content h2 { font-size: 1.15rem; color: #F59E0B; }
        .tiptap-content h3 { font-size: 1rem; }
        .tiptap-content p { margin: 0.35rem 0; line-height: 1.55; }
        .tiptap-content strong, .tiptap-content b { color: #FFFFFF; font-weight: 700; }
        .tiptap-content em, .tiptap-content i { font-style: italic; }
        .tiptap-content u { text-decoration: underline; text-decoration-color: #F59E0B; text-decoration-thickness: 2px; }
        .tiptap-content ul { list-style: disc; padding-left: 1.25rem; margin: 0.4rem 0; }
        .tiptap-content ol { list-style: decimal; padding-left: 1.25rem; margin: 0.4rem 0; }
        .tiptap-content li { margin: 0.15rem 0; }
        .tiptap-content li > p { margin: 0; }
      `}</style>
    </div>
  );
}
