"use client";

import { useState, useEffect } from "react";
import type { StudentProfile } from "@/lib/types";

interface ProfilePanelProps {
  profile: StudentProfile | null;
  onSave: (profile: StudentProfile | null) => void;
  onClose: () => void;
}

const DEGREE_OPTIONS = ["MS", "PhD", "MBA", "BS", "MEng", "MFA", "Other"];

function toNum(val: string): number | undefined {
  const n = parseFloat(val);
  return isNaN(n) ? undefined : n;
}

function toInt(val: string): number | undefined {
  const n = parseInt(val, 10);
  return isNaN(n) ? undefined : n;
}

export default function ProfilePanel({
  profile,
  onSave,
  onClose,
}: ProfilePanelProps) {
  const [form, setForm] = useState<Record<string, string>>({});
  const [englishTest, setEnglishTest] = useState<"toefl" | "ielts">("toefl");
  const [needsFunding, setNeedsFunding] = useState(false);

  // Populate form from existing profile on mount / profile change
  useEffect(() => {
    if (profile) {
      setForm({
        gpa: profile.gpa?.toString() ?? "",
        gpa_scale: profile.gpa_scale?.toString() ?? "4.0",
        undergrad_institution: profile.undergrad_institution ?? "",
        undergrad_country: profile.undergrad_country ?? "",
        major: profile.major ?? "",
        degree_target: profile.degree_target ?? "",
        field_target: profile.field_target ?? "",
        gre_quant: profile.gre_quant?.toString() ?? "",
        gre_verbal: profile.gre_verbal?.toString() ?? "",
        gmat_score: profile.gmat_score?.toString() ?? "",
        toefl_score: profile.toefl_score?.toString() ?? "",
        ielts_score: profile.ielts_score?.toString() ?? "",
        work_experience_years: profile.work_experience_years?.toString() ?? "",
        research_papers: profile.research_papers?.toString() ?? "",
        budget_total_usd: profile.budget_total_usd?.toString() ?? "",
      });
      setNeedsFunding(profile.needs_funding ?? false);
      if (profile.ielts_score) setEnglishTest("ielts");
    } else {
      setForm({ gpa_scale: "4.0" });
      setNeedsFunding(false);
    }
  }, [profile]);

  const set = (key: string, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSave = () => {
    const built: StudentProfile = {
      gpa: toNum(form.gpa ?? ""),
      gpa_scale: toNum(form.gpa_scale ?? "") ?? 4.0,
      undergrad_institution: form.undergrad_institution || undefined,
      undergrad_country: form.undergrad_country || undefined,
      major: form.major || undefined,
      degree_target: form.degree_target || undefined,
      field_target: form.field_target || undefined,
      gre_quant: toInt(form.gre_quant ?? ""),
      gre_verbal: toInt(form.gre_verbal ?? ""),
      gmat_score: toInt(form.gmat_score ?? ""),
      toefl_score: englishTest === "toefl" ? toInt(form.toefl_score ?? "") : undefined,
      ielts_score: englishTest === "ielts" ? toNum(form.ielts_score ?? "") : undefined,
      work_experience_years: toNum(form.work_experience_years ?? ""),
      research_papers: toInt(form.research_papers ?? ""),
      budget_total_usd: toInt(form.budget_total_usd ?? ""),
      needs_funding: needsFunding,
    };
    // Remove all undefined keys to keep payload clean
    const cleaned = Object.fromEntries(
      Object.entries(built).filter(([, v]) => v !== undefined)
    ) as StudentProfile;
    onSave(cleaned);
    onClose();
  };

  const handleClear = () => {
    onSave(null);
    onClose();
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 z-20 md:hidden"
        onClick={onClose}
      />

      {/* Panel */}
      <aside className="fixed right-0 top-0 h-full w-full max-w-sm bg-white shadow-xl z-30 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-800">My Profile</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close profile panel"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable form body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5 text-sm">
          {/* Privacy note */}
          <div className="bg-indigo-50 border border-indigo-100 rounded-lg px-3 py-2 text-xs text-indigo-700">
            Your profile helps Campus Compass give personalized advice. It&apos;s stored
            locally in your browser — we never save it on our servers.
          </div>

          {/* Academic background */}
          <section>
            <h3 className="font-semibold text-gray-600 mb-3 uppercase tracking-wide text-xs">
              Academic Background
            </h3>
            <div className="space-y-3">
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="block text-gray-600 mb-1">GPA</label>
                  <input
                    type="number" step="0.01" min="0" max="10"
                    placeholder="3.8"
                    value={form.gpa ?? ""}
                    onChange={(e) => set("gpa", e.target.value)}
                    className="input-field"
                  />
                </div>
                <div className="w-24">
                  <label className="block text-gray-600 mb-1">Scale</label>
                  <input
                    type="number" step="0.1" min="1" max="10"
                    placeholder="4.0"
                    value={form.gpa_scale ?? "4.0"}
                    onChange={(e) => set("gpa_scale", e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>

              <Field label="Undergraduate Institution">
                <input value={form.undergrad_institution ?? ""} onChange={(e) => set("undergrad_institution", e.target.value)} className="input-field" placeholder="e.g. IIT Bombay" />
              </Field>

              <Field label="Country">
                <input value={form.undergrad_country ?? ""} onChange={(e) => set("undergrad_country", e.target.value)} className="input-field" placeholder="e.g. India" />
              </Field>

              <Field label="Major">
                <input value={form.major ?? ""} onChange={(e) => set("major", e.target.value)} className="input-field" placeholder="e.g. Computer Science" />
              </Field>
            </div>
          </section>

          {/* Target Program */}
          <section>
            <h3 className="font-semibold text-gray-600 mb-3 uppercase tracking-wide text-xs">
              Target Program
            </h3>
            <div className="space-y-3">
              <Field label="Degree">
                <select value={form.degree_target ?? ""} onChange={(e) => set("degree_target", e.target.value)} className="input-field">
                  <option value="">Select degree</option>
                  {DEGREE_OPTIONS.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </Field>

              <Field label="Field / Discipline">
                <input value={form.field_target ?? ""} onChange={(e) => set("field_target", e.target.value)} className="input-field" placeholder="e.g. Computer Science" />
              </Field>
            </div>
          </section>

          {/* Test Scores */}
          <section>
            <h3 className="font-semibold text-gray-600 mb-3 uppercase tracking-wide text-xs">
              Test Scores
            </h3>
            <div className="space-y-3">
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="block text-gray-600 mb-1">GRE Quant</label>
                  <input type="number" min="130" max="170" placeholder="165" value={form.gre_quant ?? ""} onChange={(e) => set("gre_quant", e.target.value)} className="input-field" />
                </div>
                <div className="flex-1">
                  <label className="block text-gray-600 mb-1">GRE Verbal</label>
                  <input type="number" min="130" max="170" placeholder="155" value={form.gre_verbal ?? ""} onChange={(e) => set("gre_verbal", e.target.value)} className="input-field" />
                </div>
              </div>

              <Field label="GMAT">
                <input type="number" placeholder="700" value={form.gmat_score ?? ""} onChange={(e) => set("gmat_score", e.target.value)} className="input-field" />
              </Field>

              {/* English test toggle */}
              <div>
                <label className="block text-gray-600 mb-2">English Test</label>
                <div className="flex rounded-lg border border-gray-200 overflow-hidden mb-2">
                  {(["toefl", "ielts"] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setEnglishTest(t)}
                      className={`flex-1 py-1.5 text-xs font-medium transition-colors ${englishTest === t ? "bg-indigo-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
                    >
                      {t.toUpperCase()}
                    </button>
                  ))}
                </div>
                {englishTest === "toefl" ? (
                  <input type="number" placeholder="105" value={form.toefl_score ?? ""} onChange={(e) => set("toefl_score", e.target.value)} className="input-field" />
                ) : (
                  <input type="number" step="0.5" placeholder="7.5" value={form.ielts_score ?? ""} onChange={(e) => set("ielts_score", e.target.value)} className="input-field" />
                )}
              </div>
            </div>
          </section>

          {/* Experience & Budget */}
          <section>
            <h3 className="font-semibold text-gray-600 mb-3 uppercase tracking-wide text-xs">
              Experience & Budget
            </h3>
            <div className="space-y-3">
              <Field label="Work Experience (years)">
                <input type="number" step="0.5" placeholder="2" value={form.work_experience_years ?? ""} onChange={(e) => set("work_experience_years", e.target.value)} className="input-field" />
              </Field>

              <Field label="Research Papers Published">
                <input type="number" min="0" placeholder="0" value={form.research_papers ?? ""} onChange={(e) => set("research_papers", e.target.value)} className="input-field" />
              </Field>

              <Field label="Total Budget (USD)">
                <input type="number" step="1000" placeholder="80000" value={form.budget_total_usd ?? ""} onChange={(e) => set("budget_total_usd", e.target.value)} className="input-field" />
              </Field>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={needsFunding}
                  onChange={(e) => setNeedsFunding(e.target.checked)}
                  className="w-4 h-4 rounded text-indigo-600 border-gray-300 focus:ring-indigo-500"
                />
                <span className="text-gray-700">I need funding / assistantship</span>
              </label>
            </div>
          </section>
        </div>

        {/* Footer buttons */}
        <div className="px-5 py-4 border-t border-gray-200 flex gap-3">
          <button
            onClick={handleClear}
            className="flex-1 py-2 rounded-lg border border-gray-200 text-gray-600 text-sm hover:bg-gray-50 transition-colors"
          >
            Clear
          </button>
          <button
            onClick={handleSave}
            className="flex-1 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            Save Profile
          </button>
        </div>
      </aside>
    </>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}
