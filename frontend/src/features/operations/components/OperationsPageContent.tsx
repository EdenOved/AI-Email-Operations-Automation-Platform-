"use client";

import { PageCard } from "@/components/shared/PageCard";
import { pct } from "@/lib/format";
import { useOperations } from "@/features/operations/hooks/useOperations";

export function OperationsPageContent() {
  const { summary, status, load, liveCheck } = useOperations();

  return (
    <main>
      <PageCard>
        <h1>Operations</h1>
        <p className="muted">Health, routing outcomes, business value, integration reliability, and latest eval signal.</p>
        <div className="row">
          <button onClick={() => void load()}>Refresh</button>
          <button className="primary" onClick={() => void liveCheck()}>Run live connectivity check</button>
        </div>
      </PageCard>

      {!summary ? <PageCard>Loading...</PageCard> : (
        <>
          <PageCard>
            <h3>System health</h3>
            <div className="row">
              <div><strong>{summary.emails_total_today}</strong><div className="muted">Emails today</div></div>
              <div><strong>{summary.emails_processed_today}</strong><div className="muted">Processed</div></div>
              <div><strong>{summary.failure_count}</strong><div className="muted">Failures</div></div>
              <div><strong>{summary.hitl_pending_today}</strong><div className="muted">HITL pending</div></div>
              <div><strong>{pct(summary.integration_success_rate)}</strong><div className="muted">Integration success</div></div>
            </div>
          </PageCard>

          <PageCard>
            <h3>Automation outcomes</h3>
            <pre>{JSON.stringify(summary.route_distribution, null, 2)}</pre>
          </PageCard>

          <PageCard>
            <h3>Business value</h3>
            <div className="row">
              <div><strong>{summary.business_value.estimated_human_hours_saved_today}</strong><div className="muted">Est. hours saved</div></div>
              <div><strong>{pct(summary.business_value.automation_share_of_processed_today)}</strong><div className="muted">Automation share</div></div>
              <div><strong>{summary.business_value.processed_after_human_review_today}</strong><div className="muted">After human review</div></div>
            </div>
            <div className="muted">{summary.business_value.notes}</div>
          </PageCard>

          <PageCard>
            <h3>Latest eval snapshot</h3>
            <pre>{JSON.stringify(summary.latest_completed_eval_snapshot, null, 2)}</pre>
          </PageCard>
        </>
      )}

      <PageCard>
        <h3>Integration config status</h3>
        <pre>{JSON.stringify(status, null, 2)}</pre>
      </PageCard>
    </main>
  );
}
