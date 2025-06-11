
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { corsHeaders } from "../_shared/cors.ts";

// LiveKit JWT generation (simplified version - in production use the official SDK)
function generateLiveKitToken(roomName: string, participantName: string): string {
  const apiKey = Deno.env.get('LIVEKIT_API_KEY');
  const apiSecret = Deno.env.get('LIVEKIT_API_SECRET');
  
  if (!apiKey || !apiSecret) {
    throw new Error('LiveKit credentials not configured');
  }

  // JWT payload for LiveKit
  const payload = {
    iss: apiKey,
    sub: participantName,
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + (6 * 60 * 60), // 6 hours
    nbf: Math.floor(Date.now() / 1000) - 60, // 1 minute ago
    room: {
      join: true,
      name: roomName,
    },
    participant: {
      identity: participantName,
      name: participantName,
    },
    video: {
      room_join: true,
      can_publish: true,
      can_subscribe: true,
    },
  };

  // Simple JWT encoding (in production, use proper library)
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payloadEncoded = btoa(JSON.stringify(payload));
  
  const signature = btoa(
    Array.from(
      new Uint8Array(
        new TextEncoder().encode(`${header}.${payloadEncoded}${apiSecret}`)
      )
    ).map(b => String.fromCharCode(b)).join('')
  );

  return `${header}.${payloadEncoded}.${signature}`;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    // Get auth token from request
    const authHeader = req.headers.get('authorization');
    if (!authHeader) {
      throw new Error('No authorization header');
    }

    // Initialize Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseAnonKey, {
      global: { headers: { Authorization: authHeader } }
    });

    // Verify user is authenticated
    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      throw new Error('Unauthorized');
    }

    // Get request body
    const { roomId } = await req.json();
    if (!roomId) {
      throw new Error('Room ID is required');
    }

    // Generate token
    const participantName = user.email || user.id;
    const token = generateLiveKitToken(roomId, participantName);

    return new Response(
      JSON.stringify({ 
        token,
        serverUrl: 'wss://sage-livekit.livekit.cloud',
        participantName
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('Error generating LiveKit token:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { 
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    );
  }
});
