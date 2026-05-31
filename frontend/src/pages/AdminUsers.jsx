import { useEffect, useState } from "react";
import { api, ROLE_LABEL } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PageHeader, Card, Empty } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { PencilSimple, Trash, FloppyDisk, X } from "@phosphor-icons/react";

const INP = "bg-zinc-950 border-zinc-800 rounded-sm mt-1.5";
const INP_INLINE = "bg-zinc-950 border-zinc-800 rounded-sm h-8 text-xs font-mono";

export default function AdminUsers() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({ email: "", password: "", name: "", role: "tim_lid" });
  const [busy, setBusy] = useState(false);
  const [editId, setEditId] = useState(null);
  const [editDraft, setEditDraft] = useState({});

  async function load() {
    try { const { data } = await api.get("/auth/users"); setUsers(data); } catch {}
  }
  useEffect(() => { load(); }, []);

  async function submit(e) {
    e.preventDefault(); setBusy(true);
    try {
      await api.post("/auth/register", form);
      toast.success("User dibuat.");
      setForm({ email: "", password: "", name: "", role: "tim_lid" });
      load();
    } catch (e2) { toast.error(e2.response?.data?.detail || "Gagal."); }
    finally { setBusy(false); }
  }

  function startEdit(u) {
    setEditId(u.id);
    setEditDraft({ name: u.name, email: u.email, role: u.role, password: "" });
  }
  function cancelEdit() { setEditId(null); setEditDraft({}); }

  async function saveEdit(uid) {
    setBusy(true);
    try {
      const payload = { name: editDraft.name, email: editDraft.email, role: editDraft.role };
      if (editDraft.password && editDraft.password.trim()) payload.password = editDraft.password;
      await api.patch(`/auth/users/${uid}`, payload);
      toast.success("User diperbarui.");
      cancelEdit();
      load();
    } catch (e2) { toast.error(e2.response?.data?.detail || "Gagal menyimpan."); }
    finally { setBusy(false); }
  }

  async function deleteUser(u) {
    if (!confirm(`Hapus user ${u.name} (${u.email})? Aksi ini tidak bisa di-undo.`)) return;
    try {
      await api.delete(`/auth/users/${u.id}`);
      toast.success("User dihapus.");
      if (editId === u.id) cancelEdit();
      load();
    } catch (e2) { toast.error(e2.response?.data?.detail || "Gagal menghapus."); }
  }

  return (
    <div data-testid="admin-users-page">
      <PageHeader overline="ADMIN" title="Manajemen User" subtitle="Tambah, edit, hapus & atur role" />
      <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Tambah User" color="#F59E0B" testid="user-form-card">
          <form onSubmit={submit} className="space-y-4" data-testid="user-form">
            <Field label="Nama"><Input data-testid="user-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className={INP} /></Field>
            <Field label="Email"><Input data-testid="user-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required className={INP} /></Field>
            <Field label="Password"><Input data-testid="user-password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required className={INP} /></Field>
            <Field label="Role">
              <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                <SelectTrigger data-testid="user-role" className={INP}><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.keys(ROLE_LABEL).map((k) => <SelectItem key={k} value={k}>{ROLE_LABEL[k]}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Button type="submit" disabled={busy} data-testid="user-submit" className="w-full bg-amber-500 hover:bg-amber-400 text-zinc-950 btn-tactical rounded-sm h-10">
              {busy ? "Membuat..." : "Buat User"}
            </Button>
          </form>
        </Card>

        <Card title="Daftar User" testid="user-list-card" className="lg:col-span-2">
          {users.length === 0 ? <Empty /> : (
            <table className="w-full text-xs">
              <thead>
                <tr className="overline text-left border-b border-zinc-800">
                  <th className="pb-2 pr-2">Nama</th>
                  <th className="pb-2 pr-2">Email</th>
                  <th className="pb-2 pr-2">Role</th>
                  <th className="pb-2 pr-2">Password</th>
                  <th className="pb-2 pr-2 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const isEditing = editId === u.id;
                  const isSelf = me?.id === u.id;
                  return (
                    <tr key={u.id} className={`border-t border-zinc-800 ${isEditing ? "bg-amber-500/5" : ""}`} data-testid={`user-row-${u.id}`}>
                      {isEditing ? (
                        <>
                          <td className="py-2 pr-2">
                            <Input data-testid={`edit-name-${u.id}`} value={editDraft.name} onChange={(e) => setEditDraft({ ...editDraft, name: e.target.value })} className={INP_INLINE} />
                          </td>
                          <td className="py-2 pr-2">
                            <Input data-testid={`edit-email-${u.id}`} type="email" value={editDraft.email} onChange={(e) => setEditDraft({ ...editDraft, email: e.target.value })} className={INP_INLINE} />
                          </td>
                          <td className="py-2 pr-2">
                            <Select value={editDraft.role} onValueChange={(v) => setEditDraft({ ...editDraft, role: v })}>
                              <SelectTrigger data-testid={`edit-role-${u.id}`} className={INP_INLINE}><SelectValue /></SelectTrigger>
                              <SelectContent>
                                {Object.keys(ROLE_LABEL).map((k) => <SelectItem key={k} value={k}>{ROLE_LABEL[k]}</SelectItem>)}
                              </SelectContent>
                            </Select>
                          </td>
                          <td className="py-2 pr-2">
                            <Input
                              data-testid={`edit-password-${u.id}`}
                              type="text"
                              placeholder="(kosong = tidak diubah)"
                              value={editDraft.password || ""}
                              onChange={(e) => setEditDraft({ ...editDraft, password: e.target.value })}
                              className={INP_INLINE}
                            />
                          </td>
                          <td className="py-2 text-right whitespace-nowrap">
                            <button onClick={() => saveEdit(u.id)} disabled={busy} data-testid={`save-${u.id}`} className="text-emerald-400 hover:text-emerald-300 p-1.5" title="Simpan">
                              <FloppyDisk size={14} weight="bold" />
                            </button>
                            <button onClick={cancelEdit} data-testid={`cancel-${u.id}`} className="text-zinc-500 hover:text-zinc-300 p-1.5" title="Batal">
                              <X size={14} weight="bold" />
                            </button>
                          </td>
                        </>
                      ) : (
                        <>
                          <td className="py-2 pr-2 font-bold">{u.name}{isSelf && <span className="ml-2 text-[9px] font-mono text-amber-400 px-1 rounded-sm bg-amber-500/10">ANDA</span>}</td>
                          <td className="py-2 pr-2 font-mono text-zinc-400">{u.email}</td>
                          <td className="py-2 pr-2">
                            <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm bg-amber-500/15 text-amber-400">{ROLE_LABEL[u.role]}</span>
                          </td>
                          <td className="py-2 pr-2 font-mono text-zinc-600">••••••••</td>
                          <td className="py-2 text-right whitespace-nowrap">
                            <button onClick={() => startEdit(u)} data-testid={`edit-${u.id}`} className="text-zinc-500 hover:text-amber-400 p-1.5" title="Edit">
                              <PencilSimple size={14} weight="bold" />
                            </button>
                            <button
                              onClick={() => deleteUser(u)}
                              disabled={isSelf}
                              data-testid={`delete-${u.id}`}
                              className="text-zinc-500 hover:text-red-400 p-1.5 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:text-zinc-500"
                              title={isSelf ? "Tidak bisa hapus akun sendiri" : "Hapus"}
                            >
                              <Trash size={14} weight="bold" />
                            </button>
                          </td>
                        </>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}

function Field({ label, children }) { return (<div><Label className="overline">{label}</Label>{children}</div>); }
