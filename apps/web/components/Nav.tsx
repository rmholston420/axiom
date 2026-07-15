"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Network, Settings, BookMarked, Users } from "lucide-react";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/graph", label: "Graph", icon: Network },
  { href: "/council", label: "Council", icon: Users },
  { href: "/axioms", label: "Axioms", icon: BookMarked },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav
      style={{
        minWidth: 220,
        padding: "1.5rem 1rem",
        borderRight: "1px solid var(--color-border)",
        background: "var(--color-surface)",
        display: "flex",
        flexDirection: "column",
        gap: "0.35rem",
      }}
    >
      <div style={{ marginBottom: "1.5rem", paddingInline: "0.25rem" }}>
        <div style={{ fontSize: "1.15rem", fontWeight: 700, color: "var(--color-primary)" }}>
          Axiom
        </div>
        <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
          Local Research Workbench
        </div>
      </div>

      {links.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);

        return (
          <Link
            key={href}
            href={href}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.625rem",
              padding: "0.65rem 0.8rem",
              borderRadius: "var(--radius-md)",
              color: active ? "var(--color-primary)" : "var(--color-text-muted)",
              background: active
                ? "color-mix(in oklab, var(--color-primary) 12%, transparent)"
                : "transparent",
              border: active ? "1px solid color-mix(in oklab, var(--color-primary) 35%, transparent)" : "1px solid transparent",
              transition: "all 180ms ease",
            }}
          >
            <Icon size={16} />
            <span style={{ fontSize: "0.92rem", fontWeight: active ? 600 : 500 }}>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
