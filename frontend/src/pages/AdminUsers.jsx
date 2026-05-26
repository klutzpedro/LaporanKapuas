import { useEffect, useState } from "react";
import { api, ROLE_LABEL } from "@/lib/api";
import { PageHeader, Card, Empty } from "@/components/Shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

const INP = "bg-zinc-950 border-zinc-800 rounded-sm mt-1.5";

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({ email: "", password: "", name: "", role: "tim_lid" });
  const [busy, setBusy] = useState(false);

  async function load() { try { const { data } = await api.get("/auth/users"); setUsers(data); } catch {} }
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

  return (
    <div data-testid="admin-users-page">
      <PageHeader overline="ADMIN" title="Manajemen User" subtitle="Tambahkan anggota tim & atur role" />
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
                <tr className="overline text-left">
                  <th className="pb-2">Nama</th><th className="pb-2">Email</th><th className="pb-2">Role</th><th className="pb-2">Dibuat</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-t border-zinc-800" data-testid={`user-row-${u.id}`}>
                    <td className="py-2">{u.name}</td>
                    <td className="py-2 font-mono">{u.email}</td>
                    <td><span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded-sm bg-amber-500/15 text-amber-400">{ROLE_LABEL[u.role]}</span></td>
                    <td className="py-2 font-mono text-zinc-500">{u.created_at?.slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}

function Field({ label, children }) { return (<div><Label className="overline">{label}</Label>{children}</div>); }
