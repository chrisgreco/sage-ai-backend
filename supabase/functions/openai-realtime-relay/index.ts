
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  const { headers } = req;
  const upgradeHeader = headers.get("upgrade") || "";

  if (upgradeHeader.toLowerCase() !== "websocket") {
    return new Response("Expected WebSocket connection", { 
      status: 400,
      headers: corsHeaders 
    });
  }

  const { socket, response } = Deno.upgradeWebSocket(req);
  
  const openAIApiKey = Deno.env.get('OPENAI_API_KEY');
  if (!openAIApiKey) {
    console.error("OpenAI API key not configured");
    socket.close(1011, "OpenAI API key not configured");
    return response;
  }

  console.log("Establishing connection to OpenAI Realtime API...");

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
    console.log("Connected to OpenAI Realtime API successfully");
  };

  openAISocket.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      console.log("OpenAI message type:", message.type);
      
      // Configure session after receiving session.created
      if (message.type === 'session.created' && !sessionConfigured) {
        console.log("Configuring session...");
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
    } catch (error) {
      console.error("Error processing OpenAI message:", error);
    }
  };

  socket.onmessage = (event) => {
    try {
      // Forward client messages to OpenAI
      if (openAISocket.readyState === WebSocket.OPEN) {
        openAISocket.send(event.data);
      } else {
        console.warn("OpenAI socket not ready, message not sent");
      }
    } catch (error) {
      console.error("Error forwarding message to OpenAI:", error);
    }
  };

  socket.onclose = (event) => {
    console.log("Client disconnected:", event.code, event.reason);
    if (openAISocket.readyState === WebSocket.OPEN) {
      openAISocket.close();
    }
  };

  openAISocket.onclose = (event) => {
    console.log("OpenAI connection closed:", event.code, event.reason);
    if (socket.readyState === WebSocket.OPEN) {
      socket.close();
    }
  };

  openAISocket.onerror = (error) => {
    console.error("OpenAI WebSocket error:", error);
    if (socket.readyState === WebSocket.OPEN) {
      socket.close(1011, "OpenAI connection error");
    }
  };

  socket.onerror = (error) => {
    console.error("Client WebSocket error:", error);
    if (openAISocket.readyState === WebSocket.OPEN) {
      openAISocket.close();
    }
  };

  return response;
});
