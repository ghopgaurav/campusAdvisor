export interface StudentProfile {
  gpa?: number;
  gpa_scale?: number;
  undergrad_institution?: string;
  undergrad_country?: string;
  major?: string;
  degree_target?: string;
  field_target?: string;
  gre_quant?: number;
  gre_verbal?: number;
  gmat_score?: number;
  toefl_score?: number;
  ielts_score?: number;
  work_experience_years?: number;
  research_papers?: number;
  budget_total_usd?: number;
  needs_funding?: boolean;
  preferences?: Record<string, string>;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ToolUsageInfo {
  tool_name: string;
  query?: string;
  source_url?: string;
}

export interface ChatRequest {
  message: string;
  conversation_history: ChatMessage[];
  student_profile?: StudentProfile | null;
}

export interface ChatResponse {
  response: string;
  tools_used: ToolUsageInfo[];
  follow_up_suggestions: string[];
}

// Extends ChatMessage with UI-only fields
export interface DisplayMessage extends ChatMessage {
  id: string;
  timestamp: Date;
  tools_used?: ToolUsageInfo[];
  follow_up_suggestions?: string[];
}
