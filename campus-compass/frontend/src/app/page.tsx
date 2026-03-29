"use client";

import { useState } from "react";
import { useChat } from "@/hooks/useChat";
import ChatWindow from "@/components/ChatWindow";
import ProfilePanel from "@/components/ProfilePanel";

export default function Home() {
  const { messages, isLoading, profile, sendMessage, updateProfile, clearChat } =
    useChat();
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* ── Header ── */}
      <header className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-2xl select-none">🧭</span>
          <span className="font-semibold text-gray-800 text-lg">
            Campus Compass
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Profile indicator dot when profile is set */}
          {profile && (
            <span className="w-2 h-2 rounded-full bg-green-400" title="Profile saved" />
          )}

          <button
            onClick={() => setProfileOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-gray-600 hover:bg-gray-100 border border-gray-200 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            My Profile
          </button>

          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="px-3 py-1.5 rounded-lg text-sm text-gray-500 hover:bg-gray-100 border border-gray-200 transition-colors"
              title="Start new conversation"
            >
              New chat
            </button>
          )}
        </div>
      </header>

      {/* ── Chat area ── */}
      <main className="flex-1 overflow-hidden">
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          onSend={sendMessage}
        />
      </main>

      {/* ── Profile side panel ── */}
      {profileOpen && (
        <ProfilePanel
          profile={profile}
          onSave={updateProfile}
          onClose={() => setProfileOpen(false)}
        />
      )}
    </div>
  );
}
