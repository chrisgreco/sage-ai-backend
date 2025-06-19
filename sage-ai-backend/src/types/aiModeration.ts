
export interface AIAgent {
  name: string;
  role: string;
  active: boolean;
  persona: string;
}

export interface UseAIModerationProps {
  roomId: string;
  isConnected: boolean;
  agents: AIAgent[];
}

export interface TranscriptEntry {
  speaker: string;
  text: string;
  timestamp: Date;
}

export interface UseAIModerationReturn {
  aiConnected: boolean;
  aiConnecting: boolean;
  activeAgent: string | null;
  transcript: TranscriptEntry[];
  error: string | null;
  sendAudioToAI: (audioData: Float32Array) => void;
  connectToAI: () => void;
  disconnectFromAI: () => void;
}
