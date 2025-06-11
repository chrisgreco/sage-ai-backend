
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
  console.log("API Key available:", !!openAIApiKey);

  // Connect to OpenAI Realtime API with updated model and required headers
  const openAISocket = new WebSocket(
    "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2025-06-03",
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
    socket.send(JSON.stringify({
      type: "connection_status",
      status: "connected",
      message: "Connected to OpenAI successfully"
    }));
  };

  openAISocket.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      console.log("OpenAI message type:", message.type);
      
      // Configure session after receiving session.created
      if (message.type === 'session.created' && !sessionConfigured) {
        console.log("Configuring session with updated settings...");
        const sessionUpdate = {
          type: 'session.update',
          session: {
            modalities: ['text', 'audio'],
            instructions: 'You are an AI moderator for debates. Your role depends on your assigned persona: Socrates (ask clarifying questions), Solon (enforce rules), Buddha (maintain peaceful tone), Hermes (summarize and transition), or Aristotle (fact-check). Only speak when your specific role is needed. Keep interventions brief and polite.',
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
        console.log("Session configuration sent");
      }

      // Forward all messages to client
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(event.data);
      }
    } catch (error) {
      console.error("Error processing OpenAI message:", error);
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
          type: "error",
          error: { message: `Error processing OpenAI message: ${error.message}` }
        }));
      }
    }
  };

  openAISocket.onerror = (error) => {
    console.error("OpenAI WebSocket error:", error);
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        type: "error",
        error: { message: "OpenAI connection error - check API key and permissions" }
      }));
    }
  };

  socket.onmessage = (event) => {
    try {
      if (openAISocket.readyState === WebSocket.OPEN) {
        console.log("Forwarding message to OpenAI");
        openAISocket.send(event.data);
      } else {
        console.warn("OpenAI socket not ready, current state:", openAISocket.readyState);
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({
            type: "error",
            error: { message: "OpenAI connection not ready" }
          }));
        }
      }
    } catch (error) {
      console.error("Error forwarding message to OpenAI:", error);
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
          type: "error",
          error: { message: `Error sending to OpenAI: ${error.message}` }
        }));
      }
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
      socket.send(JSON.stringify({
        type: "connection_status",
        status: "disconnected",
        message: `OpenAI connection closed: ${event.reason || 'Unknown reason'}`
      }));
      socket.close();
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
