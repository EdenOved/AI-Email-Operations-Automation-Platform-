import "./globals.css";
import Link from "next/link";
import type { ReactNode } from "react";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="topnav">
          <Link href="/cases">Cases</Link>
          <Link href="/approvals">Approvals</Link>
          <Link href="/operations">Operations</Link>
          <Link href="/evals">Evals</Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
