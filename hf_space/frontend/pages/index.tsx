import React from 'react';
export default function Home() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-4">Payment Retry Orchestrator</h1>
        <p className="text-gray-400 mb-8">Payment retry with exponential backoff and idempotency</p>
        <div className="bg-gray-900 rounded-xl p-6">
          <h2 className="text-xl font-semibold mb-4">API Endpoints</h2>
          <ul className="space-y-2 text-gray-300"><li>/payments</li>
<li>/payments/{id}/retry</li>
<li>/payments/history</li></ul>
        </div>
      </div>
    </div>
  );
}
