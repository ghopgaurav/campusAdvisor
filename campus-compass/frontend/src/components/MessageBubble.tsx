"use client";

import ReactMarkdown from "react-markdown";
import type { DisplayMessage } from "@/lib/types";
import { ToolBadgeList } from "./ToolBadge";
import SuggestionChips from "./SuggestionChips";

interface MessageBubbleProps {
  message: DisplayMessage;
  onSuggestionClick: (suggestion: string) => void;
}

export default function MessageBubble({
  message,
  onSuggestionClick,
}: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex w-full animate-fadeIn ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div className={`max-w-[85%] md:max-w-[75%] ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        {/* Bubble */}
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? "bg-indigo-600 text-white rounded-br-sm"
              : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm"
          }`}
        >
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
          ) : (
            <div className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-headings:font-semibold prose-p:text-gray-700 prose-p:leading-relaxed prose-li:text-gray-700 prose-strong:text-gray-800 prose-a:text-indigo-600 prose-a:no-underline hover:prose-a:underline prose-code:bg-gray-100 prose-code:px-1 prose-code:rounded prose-table:text-sm">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Tool badges — only on assistant messages */}
        {!isUser && message.tools_used && message.tools_used.length > 0 && (
          <div className="px-1 mt-1">
            <ToolBadgeList tools={message.tools_used} />
          </div>
        )}

        {/* Follow-up suggestions — only on the last assistant message */}
        {!isUser &&
          message.follow_up_suggestions &&
          message.follow_up_suggestions.length > 0 && (
            <div className="px-1">
              <SuggestionChips
                suggestions={message.follow_up_suggestions}
                onSelect={onSuggestionClick}
              />
            </div>
          )}

        {/* Timestamp */}
        <span className="text-xs text-gray-400 mt-1 px-1">
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </div>
  );
}
