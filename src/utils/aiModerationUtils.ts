
import type { AIAgent } from '@/types/aiModeration';

export const generateModerationInstructions = (activeAgents: AIAgent[]): string => {
  const agentDescriptions = activeAgents.map(agent => 
    `${agent.name} (${agent.role}): ${agent.persona}`
  ).join('\n');

  return `You are part of a multi-agent AI moderation system for live voice debates. 

Active moderators:
${agentDescriptions}

Your role depends on your assigned persona. Only speak when your specific moderation criteria are met:
- Socrates: Ask clarifying questions when assumptions are made
- Solon: Enforce rules when violations occur (interruptions, personal attacks)
- Buddha: Intervene when tone becomes aggressive or hostile
- Hermes: Summarize key points during natural breaks
- Aristotle: Request sources for factual claims

Keep interventions brief (1-2 sentences), polite, and focused on your specific role. Only one agent should speak at a time.

The user is in a live debate. Listen carefully and only interject when necessary according to your role.`;
};

export const determineActiveAgent = (agents: AIAgent[], message?: any): string => {
  const activeAgentsList = agents.filter(a => a.active);
  if (activeAgentsList.length === 0) return 'AI Moderator';
  
  // Simple rotation for demo - in production this would be smarter
  const index = Math.floor(Math.random() * activeAgentsList.length);
  return activeAgentsList[index].name;
};

export const encodeAudioForAI = (audioData: Float32Array): string => {
  try {
    // Convert Float32Array to base64 PCM16
    const int16Array = new Int16Array(audioData.length);
    for (let i = 0; i < audioData.length; i++) {
      const s = Math.max(-1, Math.min(1, audioData[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }

    const uint8Array = new Uint8Array(int16Array.buffer);
    let binary = '';
    const chunkSize = 0x8000;
    
    for (let i = 0; i < uint8Array.length; i += chunkSize) {
      const chunk = uint8Array.subarray(i, Math.min(i + chunkSize, uint8Array.length));
      binary += String.fromCharCode.apply(null, Array.from(chunk));
    }
    
    return btoa(binary);
  } catch (err) {
    console.error('Error encoding audio for AI:', err);
    throw err;
  }
};
