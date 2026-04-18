import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { InboxRow } from "@/types/operator";

export function useCasesInbox(onlyFailures: boolean, onlyApprovals: boolean) {
  const [rows, setRows] = useState<InboxRow[]>([]);

  const load = useCallback(async () => {
    const q = new URLSearchParams({
      only_failures: String(onlyFailures),
      only_approvals: String(onlyApprovals),
      limit: "100"
    });
    const data = await api<{ items: InboxRow[] }>(`/api/v1/operator/inbox?${q.toString()}`);
    setRows(data.items);
  }, [onlyApprovals, onlyFailures]);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 10000);
    return () => clearInterval(t);
  }, [load]);

  return { rows, load };
}
