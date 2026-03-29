"use client";

import { useEffect, useRef } from "react";
import type { DisplayMessage } from "@/lib/types";
import MessageBubble from "./MessageBubble";
import InputBar from "./InputBar";
import WelcomeScreen from "./WelcomeScreen";

interface ChatWindowProps {
  messages: DisplayMessage[];
  isLoading: boolean;
  onSend: (message: string) => void;
}

function LoadingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
        <div className="flex items-center gap-2 text-gray-500 text-sm">
          <div className="flex gap-1">
            <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:0ms]" />
            <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:150ms]" />
            <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:300ms]" />
          </div>
          <span>Gathering information&hellip;</span>
        </div>
      </div>
    </div>
  );
}

export default function ChatWindow({
  messages,
  isLoading,
  onSend,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom whenever messages change or loading state changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex flex-col h-full">
      {/* Scrollable message area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 ? (
          <WelcomeScreen onPromptClick={onSend} />
        ) : (
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onSuggestionClick={onSend}
              />
            ))}
            {isLoading && <LoadingIndicator />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar pinned to bottom */}
      <InputBar onSend={onSend} isLoading={isLoading} />
    </div>
  );
}
