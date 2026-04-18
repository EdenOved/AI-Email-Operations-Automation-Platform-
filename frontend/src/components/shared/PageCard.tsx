import type { ReactNode } from "react";

export function PageCard({ children }: { children: ReactNode }) {
  return <div className="card">{children}</div>;
}
