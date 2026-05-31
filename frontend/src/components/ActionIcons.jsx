import { PencilSimple, Trash } from "@phosphor-icons/react";

/**
 * Consistent edit/delete action buttons used on team report list cards.
 * Properly contained buttons (w-8 h-8) with hover states so the icons
 * don't look "floating / berantakan" against the dark page background.
 */
export function EditButton({ onClick, testid }) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testid}
      title="Edit"
      className="w-8 h-8 rounded-sm bg-zinc-900/70 hover:bg-amber-500/15 border border-zinc-800 hover:border-amber-500/50 text-zinc-400 hover:text-amber-400 flex items-center justify-center transition-colors shrink-0"
    >
      <PencilSimple size={14} weight="bold" />
    </button>
  );
}

export function DeleteButton({ onClick, testid }) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testid}
      title="Hapus"
      className="w-8 h-8 rounded-sm bg-zinc-900/70 hover:bg-red-500/15 border border-zinc-800 hover:border-red-500/50 text-zinc-400 hover:text-red-400 flex items-center justify-center transition-colors shrink-0"
    >
      <Trash size={14} weight="bold" />
    </button>
  );
}

export function ItemActions({ onEdit, onDelete, editTestid, deleteTestid }) {
  return (
    <div className="flex gap-1.5 shrink-0">
      <EditButton onClick={onEdit} testid={editTestid} />
      <DeleteButton onClick={onDelete} testid={deleteTestid} />
    </div>
  );
}
