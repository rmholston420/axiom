"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Save } from "lucide-react";
import Shell from "@/components/Shell";
import { fetchModels, fetchSettings, saveSettings, type SettingsData } from "@/lib/api";

const defaultSettings: SettingsData = {
  axiom_model_planner: "",
  axiom_model_synthesizer: "",
  axiom_model_code: "",
  axiom_model_critic: "",
  axiom_model_chairman: "",
  axiom_model_axiomatizer: "",
  axiom_breadth: 4,
  axiom_depth: 3,
  axiom_max_results_per_query: 5,
  axiom_council_size: 3,
  axiom_council_enabled: true,
  axiom_axiomatizer_enabled: false,
};

function fieldStyle(): React.CSSProperties {
  return {
    width: "100%",
    background: "var(--color-surface-2)",
    color: "var(--color-text)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    padding: "0.8rem 0.9rem",
  };
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsData>(defaultSettings);
  const [models, setModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const [settingsData, modelsData] = await Promise.all([
          fetchSettings(),
          fetchModels(),
        ]);
        setSettings(settingsData);
        setModels(modelsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  function update<K extends keyof SettingsData>(key: K, value: SettingsData[K]) {
    setSettings((prev) => ({ ...prev, [key]: value }));
  }

  async function onSave() {
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      const response = await saveSettings(settings);
      setSettings(response);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 1800);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  const modelFields: Array<[keyof SettingsData, string]> = [
    ["axiom_model_planner", "Planner"],
    ["axiom_model_synthesizer", "Synthesizer"],
    ["axiom_model_code", "Code"],
    ["axiom_model_critic", "Critic"],
    ["axiom_model_chairman", "Chairman"],
    ["axiom_model_axiomatizer", "Axiomatizer"],
  ];

  return (
    <Shell>
      <div style={{ maxWidth: "900px", display: "grid", gap: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700 }}>Settings</h1>
            <p style={{ color: "var(--color-text-muted)", fontSize: "0.95rem" }}>
              Runtime defaults and model selection.
            </p>
          </div>
          <button
            onClick={() => void onSave()}
            disabled={saving || loading}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.8rem 1rem",
              background: saved ? "#15803d" : "var(--color-primary)",
              color: "white",
              border: "none",
              borderRadius: "var(--radius-md)",
              fontWeight: 600,
              opacity: saving || loading ? 0.7 : 1,
              cursor: saving || loading ? "not-allowed" : "pointer",
            }}
          >
            {saving ? (
              <Loader2 size={16} className="animate-spin" />
            ) : saved ? (
              <CheckCircle2 size={16} />
            ) : (
              <Save size={16} />
            )}
            {saving ? "Saving..." : saved ? "Saved" : "Save"}
          </button>
        </div>

        {error ? (
          <div
            style={{
              color: "#fda4af",
              background: "rgba(127,29,29,0.25)",
              border: "1px solid rgba(248,113,113,0.35)",
              borderRadius: "var(--radius-md)",
              padding: "0.85rem",
            }}
          >
            {error}
          </div>
        ) : null}

        {loading ? (
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
              color: "var(--color-text-muted)",
            }}
          >
            <Loader2 size={16} className="animate-spin" />
            Loading settings...
          </div>
        ) : (
          <>
            <section
              style={{
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-lg)",
                padding: "1rem",
              }}
            >
              <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "1rem" }}>Models</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "1rem" }}>
                {modelFields.map(([key, label]) => (
                  <label key={String(key)} style={{ display: "grid", gap: "0.45rem" }}>
                    <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>{label}</span>
                    {models.length > 0 ? (
                      <select
                        value={settings[key] as string}
                        onChange={(e) => update(key, e.target.value as SettingsData[typeof key])}
                        style={fieldStyle()}
                      >
                        <option value="">Select a model</option>
                        {models.map((model) => (
                          <option key={model} value={model}>
                            {model}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        value={settings[key] as string}
                        onChange={(e) => update(key, e.target.value as SettingsData[typeof key])}
                        style={fieldStyle()}
                      />
                    )}
                  </label>
                ))}
              </div>
            </section>

            <section
              style={{
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-lg)",
                padding: "1rem",
              }}
            >
              <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "1rem" }}>Runtime</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "1rem" }}>
                <label style={{ display: "grid", gap: "0.45rem" }}>
                  <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>Breadth</span>
                  <input
                    type="number"
                    value={settings.axiom_breadth}
                    onChange={(e) => update("axiom_breadth", Number(e.target.value))}
                    style={fieldStyle()}
                  />
                </label>

                <label style={{ display: "grid", gap: "0.45rem" }}>
                  <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>Depth</span>
                  <input
                    type="number"
                    value={settings.axiom_depth}
                    onChange={(e) => update("axiom_depth", Number(e.target.value))}
                    style={fieldStyle()}
                  />
                </label>

                <label style={{ display: "grid", gap: "0.45rem" }}>
                  <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>Max results / query</span>
                  <input
                    type="number"
                    value={settings.axiom_max_results_per_query}
                    onChange={(e) => update("axiom_max_results_per_query", Number(e.target.value))}
                    style={fieldStyle()}
                  />
                </label>

                <label style={{ display: "grid", gap: "0.45rem" }}>
                  <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>Council size</span>
                  <input
                    type="number"
                    value={settings.axiom_council_size}
                    onChange={(e) => update("axiom_council_size", Number(e.target.value))}
                    style={fieldStyle()}
                  />
                </label>

                <label style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginTop: "1.8rem" }}>
                  <input
                    type="checkbox"
                    checked={settings.axiom_council_enabled}
                    onChange={(e) => update("axiom_council_enabled", e.target.checked)}
                  />
                  <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>Council enabled</span>
                </label>

                <label style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginTop: "1.8rem" }}>
                  <input
                    type="checkbox"
                    checked={settings.axiom_axiomatizer_enabled}
                    onChange={(e) => update("axiom_axiomatizer_enabled", e.target.checked)}
                  />
                  <span style={{ fontSize: "0.9rem", fontWeight: 600 }}>Axiomatizer enabled</span>
                </label>
              </div>
            </section>
          </>
        )}
      </div>
    </Shell>
  );
}
