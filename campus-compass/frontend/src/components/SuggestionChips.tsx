interface SuggestionChipsProps {
  suggestions: string[];
  onSelect: (suggestion: string) => void;
}

export default function SuggestionChips({
  suggestions,
  onSelect,
}: SuggestionChipsProps) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mt-3">
      {suggestions.map((s) => (
        <button
          key={s}
          onClick={() => onSelect(s)}
          className="px-3 py-1.5 rounded-full border border-indigo-200 bg-white text-indigo-600 text-sm hover:bg-indigo-50 hover:border-indigo-400 transition-colors duration-150 text-left"
        >
          {s}
        </button>
      ))}
    </div>
  );
}
