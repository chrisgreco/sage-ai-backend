
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { corsHeaders } from "../_shared/cors.ts";

serve(async (req) => {
  const { headers } = req;
  const upgradeHeader = headers.get("upgrade") || "";

  if (upgradeHeader.toLowerCase() !== "websocket") {
    return new Response("Expected WebSocket connection", { status: 400 });
  }

  const { socket, response } = Deno.upgradeWebSocket(req);
  
  const openAIApiKey = Deno.env.get('OPENAI_API_KEY');
  if (!openAIApiKey) {
    socket.close(1011, "OpenAI API key not configured");
    return response;
  }

  // Connect to OpenAI Realtime API
  const openAISocket = new WebSocket(
    "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17",
    [], 
    {
      headers: {
        "Authorization": `Bearer ${openAIApiKey}`,
        "OpenAI-Beta": "realtime=v1"
      }
    }
  );

  let sessionConfigured = false;

  openAISocket.onopen = () => {
    console.log("Connected to OpenAI Realtime API");
  };

  openAISocket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    // Configure session after receiving session.created
    if (message.type === 'session.created' && !sessionConfigured) {
      const sessionUpdate = {
        type: 'session.update',
        session: {
          modalities: ['text', 'audio'],
          instructions: 'You are an AI moderator for debates. Your role depends on your assigned persona: Socrates (ask clarifying questions), Solon (enforce rules), Buddha (maintain peaceful tone), Hermes (summarize and transition), or Aristotle (fact-check). Only speak when your specific role is needed.',
          voice: 'alloy',
          input_audio_format: 'pcm16',
          output_audio_format: 'pcm16',
          input_audio_transcription: {
            model: 'whisper-1'
          },
          turn_detection: {
            type: 'server_vad',
            threshold: 0.5,
            prefix_padding_ms: 300,
            silence_duration_ms: 1000
          },
          temperature: 0.8,
          max_response_output_tokens: 'inf'
        }
      };
      
      openAISocket.send(JSON.stringify(sessionUpdate));
      sessionConfigured = true;
    }

    // Forward all messages to client
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(event.data);
    }
  };

  socket.onmessage = (event) => {
    // Forward client messages to OpenAI
    if (openAISocket.readyState === WebSocket.OPEN) {
      openAISocket.send(event.data);
    }
  };

  socket.onclose = () => {
    console.log("Client disconnected");
    openAISocket.close();
  };

  openAISocket.onclose = () => {
    console.log("OpenAI connection closed");
    socket.close();
  };

  openAISocket.onerror = (error) => {
    console.error("OpenAI WebSocket error:", error);
    socket.close(1011, "OpenAI connection error");
  };

  return response;
});
