import { useEffect, useRef, useState } from "react";
import { UploadSimple, X } from "@phosphor-icons/react";

export default function ImageUploader({ value, onChange, label = "Upload Gambar", testid }) {
  const inputRef = useRef(null);
  const [preview, setPreview] = useState(value || "");

  useEffect(() => setPreview(value || ""), [value]);

  function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) {
      alert("Ukuran gambar maksimal 4 MB.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result;
      setPreview(dataUrl);
      onChange?.(dataUrl);
    };
    reader.readAsDataURL(file);
  }

  function clear() {
    setPreview("");
    onChange?.(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div className="space-y-2" data-testid={testid}>
      <p className="overline">{label}</p>
      {preview ? (
        <div className="relative inline-block">
          <img src={preview} alt="preview" className="max-h-40 max-w-full rounded-sm border border-zinc-800" />
          <button
            type="button"
            onClick={clear}
            data-testid={`${testid}-clear`}
            className="absolute -top-2 -right-2 bg-red-500 text-white w-6 h-6 rounded-full flex items-center justify-center hover:bg-red-400"
          >
            <X size={12} weight="bold" />
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          data-testid={`${testid}-button`}
          className="border border-dashed border-zinc-700 hover:border-amber-500 hover:text-amber-400 text-zinc-400 rounded-sm w-full px-4 py-6 text-xs font-mono flex flex-col items-center gap-2 transition-colors"
        >
          <UploadSimple size={20} />
          KLIK UNTUK UPLOAD GAMBAR (MAX 4MB)
        </button>
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        onChange={handleFile}
        className="hidden"
      />
    </div>
  );
}
