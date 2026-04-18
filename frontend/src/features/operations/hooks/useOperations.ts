import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { OperationsSummary } from "@/types/operator";

export function useOperations() {
  const [summary, setSummary] = useState<OperationsSummary | null>(null);
  const [status, setStatus] = useState<any>(null);

  const load = useCallback(async () => {
    const [s, i] = await Promise.all([
      api<OperationsSummary>("/api/v1/operator/operations/summary"),
      api<any>("/api/v1/operator/integrations/status?live=false")
    ]);
    setSummary(s);
    setStatus(i);
  }, []);

  const liveCheck = useCallback(async () => {
    setStatus(await api<any>("/api/v1/operator/integrations/status?live=true"));
  }, []);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 12000);
    return () => clearInterval(t);
  }, [load]);

  return { summary, status, load, liveCheck };
}
