"use client";

import { PageCard } from "@/components/shared/PageCard";
import { StatusPill } from "@/components/ui/StatusPill";
import { iso } from "@/lib/format";
import { useCaseDetail } from "@/features/cases/hooks/useCaseDetail";

export function CaseDetailPageContent({ caseId }: { caseId: string }) {
  const { data, error, load, retryIntegrations, promoteGolden } = useCaseDetail(caseId);

  if (error) return <main><PageCard>Error: {error}</PageCard></main>;
  if (!data) return <main><PageCard>Loading...</PageCard></main>;

  return (
    <main>
      <PageCard>
        <h1>{data.email.subject || "(no subject)"}</h1>
        <p><strong>From:</strong> {data.email.from_address}</p>
        <p><strong>Status:</strong> <StatusPill value={data.email.status} /></p>
        <p className="muted">thread_id={data.email.thread_id || "-"} · in_reply_to={data.email.in_reply_to || "-"}</p>
        <div className="row">
          <button onClick={() => void load()}>Refresh</button>
          <button className="primary" onClick={() => void retryIntegrations()}>Retry integrations</button>
          <button onClick={() => void promoteGolden()}>Promote HITL to golden</button>
        </div>
      </PageCard>

      <PageCard>
        <h3>Decision quality</h3>
        <pre>{JSON.stringify(data.routing, null, 2)}</pre>
      </PageCard>

      <PageCard>
        <h3>Extraction</h3>
        <pre>{JSON.stringify(data.extraction, null, 2)}</pre>
      </PageCard>

      <PageCard>
        <h3>Email body</h3>
        <pre>{data.email.body_text || ""}</pre>
      </PageCard>

      <PageCard>
        <h3>Integration jobs</h3>
        <table>
          <thead><tr><th>Provider</th><th>Action</th><th>Status</th><th>Error</th></tr></thead>
          <tbody>
            {data.jobs.map((j) => <tr key={j.id}><td>{j.provider}</td><td>{j.action}</td><td>{j.status}</td><td>{j.error_detail || "-"}</td></tr>)}
          </tbody>
        </table>
      </PageCard>

      <PageCard>
        <h3>Integration attempts</h3>
        <table>
          <thead><tr><th>Provider</th><th>Status</th><th>Code</th><th>Error</th><th>At</th></tr></thead>
          <tbody>
            {data.attempts.map((a) => (
              <tr key={a.attempt_id}>
                <td>{a.provider}</td>
                <td>{a.status}</td>
                <td>{a.response_code ?? "-"}</td>
                <td>{a.error_detail || "-"}</td>
                <td>{iso(a.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </PageCard>
    </main>
  );
}
