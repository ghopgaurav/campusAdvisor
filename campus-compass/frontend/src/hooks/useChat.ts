"use client";

import { useState, useCallback } from "react";
import { sendMessage as apiSendMessage } from "@/lib/api";
import type {
  ChatMessage,
  DisplayMessage,
  StudentProfile,
} from "@/lib/types";

const PROFILE_STORAGE_KEY = "campus_compass_profile";

function loadProfileFromStorage(): StudentProfile | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(PROFILE_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StudentProfile) : null;
  } catch {
    return null;
  }
}

function saveProfileToStorage(profile: StudentProfile | null): void {
  if (typeof window === "undefined") return;
  try {
    if (profile) {
      localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
    } else {
      localStorage.removeItem(PROFILE_STORAGE_KEY);
    }
  } catch {
    // localStorage unavailable — silently ignore
  }
}

let _idCounter = 0;
function nextId(): string {
  return `msg-${Date.now()}-${++_idCounter}`;
}

export function useChat() {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfileState] = useState<StudentProfile | null>(
    loadProfileFromStorage
  );

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      setError(null);

      const userMsg: DisplayMessage = {
        id: nextId(),
        role: "user",
        content: text.trim(),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      // Build conversation history from existing messages (exclude the one just added)
      const history: ChatMessage[] = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      try {
        const response = await apiSendMessage({
          message: text.trim(),
          conversation_history: history,
          student_profile: profile ?? null,
        });

        const assistantMsg: DisplayMessage = {
          id: nextId(),
          role: "assistant",
          content: response.response,
          timestamp: new Date(),
          tools_used: response.tools_used,
          follow_up_suggestions: response.follow_up_suggestions,
        };

        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "An unexpected error occurred.";
        setError(message);

        // Show error inline as an assistant message so the user sees it
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            content:
              "Sorry, I ran into an error getting that information. Please try again.",
            timestamp: new Date(),
            tools_used: [],
            follow_up_suggestions: [],
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [messages, isLoading, profile]
  );

  const updateProfile = useCallback((newProfile: StudentProfile | null) => {
    setProfileState(newProfile);
    saveProfileToStorage(newProfile);
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    profile,
    sendMessage,
    updateProfile,
    clearChat,
  };
}
