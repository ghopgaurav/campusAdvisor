import type { ToolUsageInfo } from "@/lib/types";

const TOOL_LABELS: Record<string, { icon: string; label: string }> = {
  search_us_universities: { icon: "📊", label: "College Scorecard" },
  get_university_details: { icon: "📊", label: "College Scorecard" },
  fetch_university_page: { icon: "📄", label: "Page Analysis" },
  web_search: { icon: "🌐", label: "Web Search" },
  get_living_costs: { icon: "💰", label: "Cost Data" },
  search_student_discussions: { icon: "💬", label: "Community" },
};

interface ToolBadgeProps {
  tool: ToolUsageInfo;
}

export default function ToolBadge({ tool }: ToolBadgeProps) {
  const meta = TOOL_LABELS[tool.tool_name] ?? {
    icon: "🔧",
    label: tool.tool_name,
  };

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 text-xs font-medium">
      <span>{meta.icon}</span>
      <span>{meta.label}</span>
    </span>
  );
}

interface ToolBadgeListProps {
  tools: ToolUsageInfo[];
}

export function ToolBadgeList({ tools }: ToolBadgeListProps) {
  // Deduplicate by tool_name so we don't show "College Scorecard" 8 times
  const seen = new Set<string>();
  const unique = tools.filter((t) => {
    if (seen.has(t.tool_name)) return false;
    seen.add(t.tool_name);
    return true;
  });

  if (unique.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1 mt-2">
      {unique.map((t) => (
        <ToolBadge key={t.tool_name} tool={t} />
      ))}
    </div>
  );
}
