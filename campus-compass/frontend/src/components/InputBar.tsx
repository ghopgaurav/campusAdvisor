"use client";

import { useState, useRef, KeyboardEvent } from "react";

interface InputBarProps {
  onSend: (message: string) => void;
  isLoading: boolean;
}

export default function InputBar({ onSend, isLoading }: InputBarProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">
      <div className="flex items-end gap-3 max-w-4xl mx-auto">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="Ask about universities, programs, costs, or admissions..."
          rows={1}
          disabled={isLoading}
          className="flex-1 resize-none rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent disabled:opacity-50 transition-all"
        />
        <button
          onClick={handleSend}
          disabled={!text.trim() || isLoading}
          className="shrink-0 flex items-center justify-center w-11 h-11 rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          aria-label="Send message"
        >
          {isLoading ? (
            <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          )}
        </button>
      </div>
      <p className="text-center text-xs text-gray-400 mt-2">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  );
}
