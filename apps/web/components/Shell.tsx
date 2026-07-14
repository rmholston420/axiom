import Nav from "./Nav";

export default function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", minHeight: "100dvh" }}>
      <Nav />
      <main style={{ flex: 1, maxHeight: "100dvh", overflowY: "auto", padding: "2rem" }}>
        {children}
      </main>
    </div>
  );
}
