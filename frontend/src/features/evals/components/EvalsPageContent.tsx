"use client";

import { useState } from "react";
import { PageCard } from "@/components/shared/PageCard";
import { iso } from "@/lib/format";
import { useEvals } from "@/features/evals/hooks/useEvals";

export function EvalsPageContent() {
  const { dataset, runs, selected, load, createRun, openRun } = useEvals();
  const [judge, setJudge] = useState(false);

  return (
    <main>
      <PageCard>
        <h1>Evals</h1>
        <p className="muted">Golden dataset + HITL-promoted cases, eval runs, per-case results, optional judge score.</p>
        <div className="row">
          <label><input type="checkbox" checked={judge} onChange={(e) => setJudge(e.target.checked)} /> enable judge</label>
          <button className="primary" onClick={() => void createRun(judge)}>Run eval now</button>
          <button onClick={() => void load()}>Refresh</button>
        </div>
      </PageCard>

      <PageCard>
        <h3>Dataset ({dataset.length})</h3>
        <table>
          <thead><tr><th>ID</th><th>Name</th><th>Expected route</th><th>Expect HITL</th></tr></thead>
          <tbody>
            {dataset.map((c) => <tr key={c.id}><td>{c.id}</td><td>{c.name}</td><td>{c.expected_route}</td><td>{String(c.expect_hitl)}</td></tr>)}
          </tbody>
        </table>
      </PageCard>

      <PageCard>
        <h3>Runs</h3>
        <table>
          <thead><tr><th>Run</th><th>Status</th><th>Pass rate</th><th>Cases</th><th>Judge avg</th><th>Created</th></tr></thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id}>
                <td><button onClick={() => void openRun(r.id)}>{r.id.slice(0, 12)}...</button></td>
                <td>{r.status}</td>
                <td>{r.pass_rate != null ? `${(r.pass_rate * 100).toFixed(1)}%` : "-"}</td>
                <td>{r.route_pass ?? "-"} / {r.case_total ?? "-"}</td>
                <td>{r.judge_avg_overall ?? "-"}</td>
                <td>{iso(r.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </PageCard>

      {selected ? (
        <PageCard>
          <h3>Selected run detail</h3>
          <pre>{JSON.stringify(selected, null, 2)}</pre>
        </PageCard>
      ) : null}
    </main>
  );
}
