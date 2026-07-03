import { useCallback, useEffect, useRef, useState } from 'react';

type Charge = {
  id: string; amount: number; currency: string; customer_id: string;
  description: string | null; status: string; max_retries: number;
  retry_count: number; next_retry_at: string | null; created_at: string; updated_at: string;
};
type Attempt = {
  attempt_number: number; status: string; error_code: string | null;
  error_message: string | null; attempted_at: string; duration_ms: number;
};
type ChargeDetail = Charge & { attempts: Attempt[] };
type Stats = {
  total_charges: number; success_count: number; failed_count: number;
  pending_count: number; processing_count: number; success_rate: number;
  avg_attempts_to_success: number;
};

const BADGE: Record<string, string> = {
  SUCCESS: 'bg-emerald-900 text-emerald-300',
  FAILED: 'bg-red-900 text-red-300',
  PENDING: 'bg-amber-900 text-amber-300',
  PROCESSING: 'bg-indigo-900 text-indigo-300',
};

const fmt = (iso: string | null) => (iso ? new Date(iso).toLocaleTimeString() : '—');

export default function Home() {
  const [charges, setCharges] = useState<Charge[]>([]);
  const [detail, setDetail] = useState<ChargeDetail | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [amount, setAmount] = useState('49.99');
  const [maxRetries, setMaxRetries] = useState(3);
  const [busy, setBusy] = useState(false);
  const pollTimer = useRef<ReturnType<typeof setTimeout>>();

  const loadList = useCallback(async () => {
    const [c, s] = await Promise.all([
      fetch('/api/charges').then(r => r.json()),
      fetch('/api/stats').then(r => r.json()),
    ]);
    setCharges(c);
    setStats(s);
  }, []);

  const loadDetail = useCallback(async (id: string) => {
    const d: ChargeDetail = await fetch(`/api/charges/${id}`).then(r => r.json());
    setDetail(d);
    clearTimeout(pollTimer.current);
    if (d.status === 'PENDING' || d.status === 'PROCESSING') {
      pollTimer.current = setTimeout(() => loadDetail(id), 800);
    } else {
      loadList();
    }
  }, [loadList]);

  useEffect(() => {
    loadList();
    return () => clearTimeout(pollTimer.current);
  }, [loadList]);

  const createCharge = async () => {
    setBusy(true);
    const res = await fetch('/api/charges', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        amount: Number(amount) || 49.99, customer_id: 'cust-demo',
        description: 'Demo charge', max_retries: maxRetries,
      }),
    });
    const data = await res.json();
    setBusy(false);
    if (res.ok) { await loadList(); loadDetail(data.id); }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">Payment Retry Orchestrator</h1>
        <p className="text-gray-400 mb-8">
          About 30% of synthetic payments fail. Failed charges retry automatically with
          exponential backoff (1s, 2s, 4s…) until they succeed or exhaust their retries — watch it live.
        </p>

        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            {[
              ['Total charges', stats.total_charges],
              ['Success rate', `${Math.round(stats.success_rate * 100)}%`],
              ['Failed', stats.failed_count],
              ['Avg attempts to success', stats.avg_attempts_to_success],
            ].map(([label, val]) => (
              <div key={label as string} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <div className="text-2xl font-bold">{val}</div>
                <div className="text-xs text-gray-500">{label}</div>
              </div>
            ))}
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          <div className="space-y-6">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="font-semibold mb-3">New charge</h2>
              <label className="block text-sm text-gray-400 mb-1">Amount (USD)</label>
              <input value={amount} onChange={e => setAmount(e.target.value)} inputMode="decimal"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mb-3" />
              <label className="block text-sm text-gray-400 mb-1">Max retries</label>
              <select value={maxRetries} onChange={e => setMaxRetries(Number(e.target.value))}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm mb-4">
                {[0, 1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
              <button onClick={createCharge} disabled={busy}
                className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 rounded-lg py-2 font-medium">
                Charge card
              </button>
            </div>

            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="font-semibold mb-3">Charges ({charges.length})</h2>
              <div className="space-y-2 max-h-80 overflow-auto">
                {charges.length === 0 && <p className="text-sm text-gray-500">None yet — create one above.</p>}
                {charges.map(c => (
                  <button key={c.id} onClick={() => loadDetail(c.id)}
                    className={`w-full text-left rounded-lg px-3 py-2 border transition-colors ${
                      detail?.id === c.id ? 'border-indigo-500 bg-gray-800' : 'border-gray-800 hover:border-gray-600'
                    }`}>
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-mono">{c.id}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${BADGE[c.status] ?? 'bg-gray-800'}`}>{c.status}</span>
                    </div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      ${c.amount.toFixed(2)} · {c.retry_count} retr{c.retry_count === 1 ? 'y' : 'ies'} used
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="lg:col-span-2">
            {!detail ? (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center text-gray-500">
                Create a charge or select one to see its attempt timeline.
              </div>
            ) : (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
                  <div>
                    <div className="font-mono text-lg">{detail.id}</div>
                    <div className="text-sm text-gray-400">
                      ${detail.amount.toFixed(2)} {detail.currency} · max {detail.max_retries} retries
                      {detail.next_retry_at && detail.status === 'PENDING' && (
                        <span className="text-amber-400"> · next retry {fmt(detail.next_retry_at)}</span>
                      )}
                    </div>
                  </div>
                  <span className={`text-sm px-3 py-1 rounded-full ${BADGE[detail.status] ?? 'bg-gray-800'} ${
                    detail.status === 'PENDING' || detail.status === 'PROCESSING' ? 'animate-pulse' : ''}`}>
                    {detail.status}
                  </span>
                </div>

                <h3 className="font-semibold mb-3 text-gray-300">Attempt timeline</h3>
                {detail.attempts.length === 0 ? (
                  <p className="text-sm text-gray-500">First attempt in flight…</p>
                ) : (
                  <div className="space-y-0">
                    {detail.attempts.map((a, i) => (
                      <div key={a.attempt_number} className="flex gap-4">
                        <div className="flex flex-col items-center">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                            a.status === 'SUCCESS' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'}`}>
                            {a.status === 'SUCCESS' ? '✓' : '✗'}
                          </div>
                          {i < detail.attempts.length - 1 && <div className="w-0.5 flex-1 bg-gray-800" />}
                        </div>
                        <div className="pb-5">
                          <div className="text-sm font-medium">
                            Attempt {a.attempt_number}
                            <span className="text-gray-500 font-normal"> · {fmt(a.attempted_at)} · {a.duration_ms}ms</span>
                          </div>
                          {a.status === 'SUCCESS' ? (
                            <div className="text-xs text-emerald-400 mt-0.5">Payment captured</div>
                          ) : (
                            <div className="text-xs text-red-400 mt-0.5">
                              {a.error_code}: {a.error_message}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    {(detail.status === 'PENDING' || detail.status === 'PROCESSING') && (
                      <div className="flex gap-4">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs bg-gray-800 border border-gray-700 text-gray-400 animate-pulse">…</div>
                        <div className="text-sm text-gray-500 pt-1.5">
                          {detail.status === 'PROCESSING' ? 'Attempting now…' : 'Waiting for backoff, retry scheduled…'}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
