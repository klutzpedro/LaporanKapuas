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

// Custom font-size mark
const FontSize = Mark.create({
  name: "fontSize",
  addAttributes() {
    return {
      size: {
        default: null,
        parseHTML: (el) => el.style.fontSize?.replace("px", "") || null,
        renderHTML: (attr) => (attr.size ? { style: `font-size: ${attr.size}px` } : {}),
      },
    };
  },
  parseHTML() { return [{ style: "font-size" }]; },
  renderHTML({ HTMLAttributes }) { return ["span", mergeAttributes(HTMLAttributes), 0]; },
  addCommands() {
    return {
      setFontSize: (size) => ({ chain }) =>
        chain().setMark(this.name, { size }).run(),
      unsetFontSize: () => ({ chain }) => chain().unsetMark(this.name).run(),
    };
  },
});

const FONTS = [
  { label: "Sans (IBM Plex)", value: "'IBM Plex Sans', sans-serif" },
  { label: "Serif", value: "Georgia, 'Times New Roman', serif" },
  { label: "Mono (IBM Plex)", value: "'IBM Plex Mono', monospace" },
  { label: "Display (Chivo)", value: "'Chivo', sans-serif" },
];

const COLORS = [
  "#FAFAFA", "#A1A1AA",
  "#F59E0B", "#EF4444", "#10B981", "#3B82F6", "#8B5CF6",
];

const SIZES = [11, 12, 13, 14, 16, 18, 20, 24];

function btn(active) {
  return `inline-flex items-center justify-center w-8 h-8 rounded-sm transition-colors ${
    active
      ? "bg-amber-500 text-zinc-950"
      : "bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-zinc-800"
  }`;
}

export default function RichEditor({ value, onChange, placeholder = "Tulis ringkasan di sini...", testid = "rich-editor" }) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
        codeBlock: false,
      }),
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

  // Sync external value changes
  useEffect(() => {
    if (!editor) return;
    const current = editor.getHTML();
    if (value && value !== current) {
      editor.commands.setContent(value, false);
    }
  }, [value, editor]);

  if (!editor) return null;

  const c = editor.chain().focus();

  return (
    <div className="border border-zinc-800 rounded-sm bg-zinc-950" data-testid={testid}>
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-1 p-2 border-b border-zinc-800 bg-zinc-900/50">
        <button type="button" onClick={() => c.toggleBold().run()} className={btn(editor.isActive("bold"))} title="Bold" data-testid={`${testid}-bold`}>
          <TextB size={14} weight="bold" />
        </button>
        <button type="button" onClick={() => c.toggleItalic().run()} className={btn(editor.isActive("italic"))} title="Italic" data-testid={`${testid}-italic`}>
          <TextItalic size={14} weight="bold" />
        </button>
        <button type="button" onClick={() => c.toggleUnderline().run()} className={btn(editor.isActive("underline"))} title="Underline" data-testid={`${testid}-underline`}>
          <TextUnderline size={14} weight="bold" />
        </button>

        <span className="w-px h-6 bg-zinc-800 mx-1" />

        <button type="button" onClick={() => c.toggleHeading({ level: 2 }).run()} className={btn(editor.isActive("heading", { level: 2 }))} title="Heading" data-testid={`${testid}-h2`}>
          <TextH size={14} weight="bold" />
        </button>
        <button type="button" onClick={() => c.toggleBulletList().run()} className={btn(editor.isActive("bulletList"))} title="Bullet list" data-testid={`${testid}-ul`}>
          <ListBullets size={14} weight="bold" />
        </button>
        <button type="button" onClick={() => c.toggleOrderedList().run()} className={btn(editor.isActive("orderedList"))} title="Numbered list" data-testid={`${testid}-ol`}>
          <ListNumbers size={14} weight="bold" />
        </button>

        <span className="w-px h-6 bg-zinc-800 mx-1" />

        {/* Font family */}
        <select
          onChange={(e) => {
            const v = e.target.value;
            v ? c.setFontFamily(v).run() : c.unsetFontFamily().run();
          }}
          defaultValue=""
          className="bg-zinc-900 border border-zinc-800 text-zinc-200 text-xs h-8 px-2 rounded-sm font-mono"
          title="Font"
          data-testid={`${testid}-font-family`}
        >
          <option value="">FONT</option>
          {FONTS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
        </select>

        {/* Font size */}
        <select
          onChange={(e) => {
            const v = e.target.value;
            v ? c.setFontSize(v).run() : c.unsetFontSize().run();
          }}
          defaultValue=""
          className="bg-zinc-900 border border-zinc-800 text-zinc-200 text-xs h-8 px-2 rounded-sm font-mono"
          title="Ukuran font"
          data-testid={`${testid}-font-size`}
        >
          <option value="">UKURAN</option>
          {SIZES.map((s) => <option key={s} value={s}>{s} px</option>)}
        </select>

        <span className="w-px h-6 bg-zinc-800 mx-1" />

        {/* Color palette */}
        <div className="flex items-center gap-1" title="Warna teks">
          <PaintBucket size={14} className="text-zinc-400" />
          {COLORS.map((col) => (
            <button
              key={col}
              type="button"
              onClick={() => c.setColor(col).run()}
              className="w-5 h-5 rounded-sm border border-zinc-700 hover:scale-110 transition-transform"
              style={{ background: col }}
              title={col}
              data-testid={`${testid}-color-${col.slice(1)}`}
            />
          ))}
          <button
            type="button"
            onClick={() => c.unsetColor().run()}
            className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 hover:text-zinc-300 ml-1 px-1.5 h-5 border border-zinc-800 rounded-sm"
            data-testid={`${testid}-color-reset`}
          >
            reset
          </button>
        </div>

        <span className="flex-1" />

        <button type="button" onClick={() => c.undo().run()} className={btn(false)} title="Undo" data-testid={`${testid}-undo`}>
          <ArrowCounterClockwise size={14} weight="bold" />
        </button>
        <button type="button" onClick={() => c.redo().run()} className={btn(false)} title="Redo" data-testid={`${testid}-redo`}>
          <ArrowClockwise size={14} weight="bold" />
        </button>
      </div>

      {/* Editor */}
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
        .tiptap-content strong { color: #FFFFFF; font-weight: 700; }
        .tiptap-content ul, .tiptap-content ol { padding-left: 1.25rem; margin: 0.4rem 0; }
        .tiptap-content li { margin: 0.15rem 0; }
        .tiptap-content u { text-decoration-color: #F59E0B; text-decoration-thickness: 2px; }
      `}</style>
    </div>
  );
}
