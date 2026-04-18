"use client";

import Link from "next/link";
import { PageCard } from "@/components/shared/PageCard";
import { iso } from "@/lib/format";
import { useApprovals } from "@/features/approvals/hooks/useApprovals";

export function ApprovalsPageContent() {
  const { rows, load, decide } = useApprovals();

  return (
    <main>
      <PageCard>
        <h1>Approvals (HITL)</h1>
        <p className="muted">Risky or low-confidence cases land here. Decide approve/reject and optionally override route.</p>
        <button onClick={() => void load()}>Refresh</button>
      </PageCard>
      <table>
        <thead><tr><th>Case</th><th>Sender</th><th>Reason</th><th>Proposed route</th><th>Created</th><th>Actions</th></tr></thead>
        <tbody>
          {rows.length === 0 ? (
            <tr><td colSpan={6}>No pending approvals.</td></tr>
          ) : rows.map((r) => (
            <tr key={r.approval_id}>
              <td><Link href={`/cases/${r.email_id}`}>{r.subject || "(no subject)"}</Link></td>
              <td>{r.from_address}</td>
              <td>{r.reason}</td>
              <td>{r.proposed_route || "-"}</td>
              <td>{iso(r.created_at)}</td>
              <td className="row">
                <button className="primary" onClick={() => void decide(r.approval_id, "approve")}>Approve</button>
                <button onClick={() => void decide(r.approval_id, "reject")}>Reject</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
