import { useCallback, useEffect, useState } from "react";
import { INTERNAL_KEY, api } from "@/lib/api";
import type { ApprovalRow } from "@/types/operator";

export function useApprovals() {
  const [rows, setRows] = useState<ApprovalRow[]>([]);

  const load = useCallback(async () => {
    const d = await api<{ items: ApprovalRow[] }>("/api/v1/operator/approvals/pending");
    setRows(d.items);
  }, []);

  const decide = useCallback(async (id: string, action: "approve" | "reject") => {
    await api(`/api/v1/operator/approvals/${id}/decide`, {
      method: "POST",
      headers: { "content-type": "application/json", "X-Internal-Key": INTERNAL_KEY },
      body: JSON.stringify({ action, reviewer: "operator-ui" })
    });
    await load();
  }, [load]);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 8000);
    return () => clearInterval(t);
  }, [load]);

  return { rows, load, decide };
}
