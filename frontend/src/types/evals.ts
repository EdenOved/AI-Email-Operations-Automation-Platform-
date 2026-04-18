export type EvalRun = {
  id: string;
  status: string;
  model: string;
  pass_rate: number | null;
  case_total: number | null;
  route_pass: number | null;
  route_fail: number | null;
  judge_avg_overall: number | null;
  created_at: string;
};
