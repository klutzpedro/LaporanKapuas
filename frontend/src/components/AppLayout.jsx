import { Outlet, Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import Sidebar from "@/components/Sidebar";
import { Toaster } from "sonner";

export default function AppLayout() {
  const { user, ready } = useAuth();
  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950 text-zinc-400 text-sm font-mono">
        Memuat sesi...
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="min-h-screen flex bg-zinc-950 text-zinc-100" data-testid="app-layout">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
      <Toaster
        theme="dark"
        position="top-right"
        toastOptions={{
          className: "!bg-zinc-900 !border !border-zinc-800 !text-zinc-100 !rounded-sm",
        }}
      />
    </div>
  );
}
