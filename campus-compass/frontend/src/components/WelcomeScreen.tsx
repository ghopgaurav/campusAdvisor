const EXAMPLE_PROMPTS = [
  "Find affordable MS CS programs with no GRE requirement",
  "Compare CMU, Georgia Tech, and UIUC for computer science",
  "What are my chances at Stanford with a 3.5 GPA and 320 GRE?",
  "How much does it cost to live in Pittsburgh as a student?",
  "What's the visa process for F-1 students?",
  "Find MS programs in data science under $40k total",
];

interface WelcomeScreenProps {
  onPromptClick: (prompt: string) => void;
}

export default function WelcomeScreen({ onPromptClick }: WelcomeScreenProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-4 py-12 text-center">
      {/* Logo */}
      <div className="text-6xl mb-4 select-none">🧭</div>
      <h1 className="text-3xl font-bold text-gray-800 mb-2">Campus Compass</h1>
      <p className="text-gray-500 text-base max-w-md mb-10">
        Evidence-backed university guidance for international students.
        Ask me anything about US graduate programs, admissions, costs, or visas.
      </p>

      {/* Example prompts */}
      <div className="w-full max-w-2xl">
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">
          Try asking
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {EXAMPLE_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => onPromptClick(prompt)}
              className="text-left px-4 py-3 rounded-xl border border-gray-200 bg-white hover:border-indigo-300 hover:bg-indigo-50 text-sm text-gray-700 transition-colors duration-150 shadow-sm"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      <p className="text-xs text-gray-400 mt-10">
        Powered by Claude · Data from College Scorecard, Reddit, and the web
      </p>
    </div>
  );
}
