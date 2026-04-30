import { create } from "zustand";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  toolsUsed?: string[];
  runId?: string;
  isStreaming?: boolean;
}

interface ChatStore {
  messages: ChatMessage[];
  addMessage: (msg: ChatMessage) => void;
  appendToken: (token: string) => void;
  finalizeAssistant: (toolsUsed: string[], runId: string) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  appendToken: (token) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant" && last.isStreaming) {
        msgs[msgs.length - 1] = { ...last, content: last.content + token };
      }
      return { messages: msgs };
    }),

  finalizeAssistant: (toolsUsed, runId) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, isStreaming: false, toolsUsed, runId };
      }
      return { messages: msgs };
    }),

  clearMessages: () => set({ messages: [] }),
}));
