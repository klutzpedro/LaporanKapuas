import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary]", error, info?.componentStack);
  }

  reset = () => {
    this.setState({ error: null });
  };

  reload = () => {
    window.location.reload();
  };

  render() {
    if (!this.state.error) return this.props.children;
    const msg = this.state.error?.message || String(this.state.error);
    return (
      <div
        data-testid="error-boundary"
        className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center p-6"
      >
        <div className="max-w-lg w-full border border-zinc-800 bg-zinc-900 rounded-sm p-6 space-y-4">
          <div className="border-l-2 border-red-500 pl-3">
            <p className="text-xs font-mono uppercase tracking-wider text-red-400">
              Terjadi Kesalahan
            </p>
            <h2 className="text-lg font-bold mt-1">Halaman gagal dimuat</h2>
          </div>
          <p className="text-sm text-zinc-400">
            Data Anda kemungkinan besar tetap tersimpan. Silakan coba lagi atau
            muat ulang halaman. Bila masih terjadi, hubungi admin.
          </p>
          <pre className="text-[11px] font-mono bg-zinc-950 border border-zinc-800 rounded-sm p-3 text-amber-300 overflow-auto max-h-32">
            {msg}
          </pre>
          <div className="flex gap-2">
            <button
              type="button"
              data-testid="error-boundary-retry"
              onClick={this.reset}
              className="flex-1 bg-amber-500 hover:bg-amber-400 text-zinc-950 text-sm font-bold uppercase tracking-wider rounded-sm h-10"
            >
              Coba Lagi
            </button>
            <button
              type="button"
              data-testid="error-boundary-reload"
              onClick={this.reload}
              className="flex-1 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-sm font-bold uppercase tracking-wider rounded-sm h-10"
            >
              Muat Ulang
            </button>
          </div>
        </div>
      </div>
    );
  }
}
