"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Save } from "lucide-react";
import Shell from "@/components/Shell";
import {
  fetchModels,
  fetchSettings,
  saveSettings,
  type SettingsData,
} from "@/lib/api";

const modelFields: (keyof SettingsData)[] = [
  "model_planner",
  "model_synthesizer",
  "model_code",
  "model_critic",
];

const numberFields: (keyof SettingsData)[] = [
  "breadth",
  "depth",
  "max_results_per_query",
];

const boolFields: (keyof SettingsData)[] = [
  "council_enabled",
  "axiomatizer_enabled",
];

const labels: Record<keyof SettingsData, string> = {
  model_planner: "Planner model",
  model_synthesizer: "Synthesizer model",
  model_code: "Code model",
  model_critic: "Critic model",
  breadth: "Breadth",
  depth: "Depth",
  max_results_per_query: "Max results / query",
  council_enabled: "Council enabled",
  axiomatizer_enabled: "Axiomatizer enabled",
};

const sectionStyle: React.CSSProperties = {
  background: "var(--color-surface)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-lg)",
  padding: "1.25rem",
  marginBottom: "1rem",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "var(--color-surface-2)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-md)",
  padding: "0.7rem 0.8rem",
  color: "var(--color-text)",
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([fetchSettings(), fetchModels()])
      .then(([settingsData, modelList]) => {
        setSettings(settingsData);
        setModels(modelList);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, []);

  function updateField<K extends keyof SettingsData>(key: K, value: SettingsData[K]) {
    setSettings((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  async function onSave() {
    if (!settings) return;
    setSaving(true);
    setError("");
    setSaved(false);

    try {
      await saveSettings(settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 1800);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Shell>
      <div style={{ maxWidth: 880, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem" }}>
          <h1 style={{ fontSize: "1.6rem", fontWeight: 700 }}>Settings</h1>
          <button
            type="button"
            onClick={() => void onSave()}
            disabled={!settings || loading || saving}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.45rem",
              padding: "0.65rem 1rem",
              border: "none",
              borderRadius: "var(--radius-md)",
              background: saved ? "var(--color-success)" : "var(--color-primary)",
              color: "white",
              fontWeight: 600,
            }}
          >
            {saving ? (
              <Loader2 size={15} className="animate-spin" />
            ) : saved ? (
              <CheckCircle2 size={15} />
            ) : (
              <Save size={15} />
            )}
            {saving ? "Saving…" : saved ? "Saved!" : "Save"}
          </button>
        </div>

        {error && (
          <div style={{ ...sectionStyle, color: "var(--color-error)" }}>{error}</div>
        )}

        {loading && (
          <div style={{ ...sectionStyle, color: "var(--color-text-muted)", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Loader2 size={16} className="animate-spin" />
            Loading settings…
          </div>
        )}

        {settings && (
          <>
            <section style={sectionStyle}>
              <h2 style={{ marginBottom: "1rem", fontSize: "1rem", fontWeight: 700 }}>Models</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "1rem" }}>
                {modelFields.map((field) => (
                  <label key={field} style={{ display: "block" }}>
                    <div style={{ fontSize: "0.82rem", color: "var(--color-text-muted)", marginBottom: "0.35rem" }}>
                      {labels[field]}
                    </div>
                    {models.length > 0 ? (
                      <select
                        value={settings[field] as string}
                        onChange={(e) => updateField(field, e.target.value as SettingsData[typeof field])}
                        style={inputStyle}
                      >
                        {models.map((model) => (
                          <option key={model} value={model}>
                            {model}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={settings[field] as string}
                        onChange={(e) => updateField(field, e.target.value as SettingsData[typeof field])}
                        style={inputStyle}
                      />
                    )}
                  </label>
                ))}
              </div>
            </section>

            <section style={sectionStyle}>
              <h2 style={{ marginBottom: "1rem", fontSize: "1rem", fontWeight: 700 }}>Runtime</h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
                {numberFields.map((field) => (
                  <label key={field} style={{ display: "block" }}>
                    <div style={{ fontSize: "0.82rem", color: "var(--color-text-muted)", marginBottom: "0.35rem" }}>
                      {labels[field]}
                    </div>
                    <input
                      type="number"
                      min={1}
                      value={settings[field] as number}
                      onChange={(e) => updateField(field, Number(e.target.value) as SettingsData[typeof field])}
                      style={inputStyle}
                    />
                  </label>
                ))}
              </div>
            </section>

            <section style={sectionStyle}>
              <h2 style={{ marginBottom: "1rem", fontSize: "1rem", fontWeight: 700 }}>Feature Flags</h2>
              <div style={{ display: "grid", gap: "0.9rem" }}>
                {boolFields.map((field) => (
                  <label key={field} style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}>
                    <input
                      type="checkbox"
                      checked={settings[field] as boolean}
                      onChange={(e) => updateField(field, e.target.checked as SettingsData[typeof field])}
                      style={{ width: 16, height: 16, accentColor: "var(--color-primary)" }}
                    />
                    <span>{labels[field]}</span>
                  </label>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </Shell>
  );
}
