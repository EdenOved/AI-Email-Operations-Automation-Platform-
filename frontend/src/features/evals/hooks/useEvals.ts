import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { EvalRun } from "@/types/evals";

export function useEvals() {
  const [dataset, setDataset] = useState<any[]>([]);
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [selected, setSelected] = useState<any | null>(null);

  const load = useCallback(async () => {
    const [d, r] = await Promise.all([
      api<{ items: any[] }>("/api/v1/operator/evals/dataset"),
      api<{ items: EvalRun[] }>("/api/v1/operator/evals/runs")
    ]);
    setDataset(d.items);
    setRuns(r.items);
  }, []);

  const createRun = useCallback(async (judge: boolean) => {
    const created = await api<{ run_id: string }>("/api/v1/operator/evals/runs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ judge_enabled: judge })
    });
    const detail = await api(`/api/v1/operator/evals/runs/${created.run_id}`);
    setSelected(detail);
    await load();
  }, [load]);

  const openRun = useCallback(async (id: string) => {
    setSelected(await api(`/api/v1/operator/evals/runs/${id}`));
  }, []);

  useEffect(() => { void load(); }, [load]);

  return { dataset, runs, selected, load, createRun, openRun };
}
