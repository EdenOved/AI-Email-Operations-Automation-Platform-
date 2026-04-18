import { useCallback, useEffect, useState } from "react";
import { INTERNAL_KEY, api } from "@/lib/api";
import type { CaseDetail } from "@/types/operator";

export function useCaseDetail(caseId: string) {
  const [data, setData] = useState<CaseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      setData(await api<CaseDetail>(`/api/v1/operator/cases/${caseId}`));
    } catch (e) {
      setError(String(e));
    }
  }, [caseId]);

  const retryIntegrations = useCallback(async () => {
    await api(`/api/v1/operator/cases/${caseId}/retry-integrations`, {
      method: "POST",
      headers: { "X-Internal-Key": INTERNAL_KEY }
    });
    await load();
  }, [caseId, load]);

  const promoteGolden = useCallback(async () => {
    await api(`/api/v1/operator/evals/golden/from-hitl`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email_id: caseId })
    });
    await load();
  }, [caseId, load]);

  useEffect(() => { void load(); }, [load]);

  return { data, error, load, retryIntegrations, promoteGolden };
}
