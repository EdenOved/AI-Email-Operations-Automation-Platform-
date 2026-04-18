"use client";

import Link from "next/link";
import { useState } from "react";
import { PageCard } from "@/components/shared/PageCard";
import { StatusPill } from "@/components/ui/StatusPill";
import { iso } from "@/lib/format";
import { useCasesInbox } from "@/features/cases/hooks/useCasesInbox";

export function CasesPageContent() {
  const [onlyFailures, setOnlyFailures] = useState(false);
  const [onlyApprovals, setOnlyApprovals] = useState(false);
  const { rows, load } = useCasesInbox(onlyFailures, onlyApprovals);

  return (
    <main>
      <PageCard>
        <h1>Cases</h1>
        <p className="muted">Main operator queue: route status, confidence, approvals, and drill-down debugging.</p>
        <div className="row">
          <label>
            <input type="checkbox" checked={onlyFailures} onChange={(e) => setOnlyFailures(e.target.checked)} /> only failures
          </label>
          <label>
            <input type="checkbox" checked={onlyApprovals} onChange={(e) => setOnlyApprovals(e.target.checked)} /> only approvals
          </label>
          <button onClick={() => void load()}>Refresh</button>
        </div>
      </PageCard>
      <table>
        <thead>
          <tr>
            <th>Subject</th>
            <th>Sender</th>
            <th>Status</th>
            <th>Route</th>
            <th>Confidence</th>
            <th>Approval</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr><td colSpan={7}>No rows yet.</td></tr>
          ) : rows.map((r) => (
            <tr key={r.email_id}>
              <td>
                <Link href={`/cases/${encodeURIComponent(r.email_id)}`}>{r.subject || "(no subject)"}</Link>
                <div className="muted">{r.email_id.slice(0, 12)}...</div>
              </td>
              <td>{r.from_address}</td>
              <td><StatusPill value={r.status} /></td>
              <td>{r.route || "-"}</td>
              <td>{r.routing_confidence != null ? r.routing_confidence.toFixed(2) : "-"}</td>
              <td>{r.approval_state || "-"}</td>
              <td>{iso(r.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
