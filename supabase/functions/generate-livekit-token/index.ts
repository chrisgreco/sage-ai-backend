
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { corsHeaders } from "../_shared/cors.ts";

// Proper HMAC-SHA256 implementation for JWT signing
async function hmacSha256(key: string, data: string): Promise<ArrayBuffer> {
  const encoder = new TextEncoder();
  const keyData = encoder.encode(key);
  const dataToSign = encoder.encode(data);
  
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  
  return await crypto.subtle.sign('HMAC', cryptoKey, dataToSign);
}

// Convert ArrayBuffer to base64url
function arrayBufferToBase64Url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  const binary = String.fromCharCode(...bytes);
  return btoa(binary)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
}

// Proper JWT token generation for LiveKit
async function generateLiveKitToken(roomName: string, participantName: string): Promise<string> {
  const apiKey = Deno.env.get('LIVEKIT_API_KEY');
  const apiSecret = Deno.env.get('LIVEKIT_API_SECRET');
  
  if (!apiKey || !apiSecret) {
    throw new Error('LiveKit credentials not configured');
  }

  const now = Math.floor(Date.now() / 1000);
  
  // JWT header
  const header = {
    alg: 'HS256',
    typ: 'JWT'
  };

  // JWT payload for LiveKit
  const payload = {
    iss: apiKey,
    sub: participantName,
    iat: now,
    exp: now + (6 * 60 * 60), // 6 hours
    nbf: now - 60, // 1 minute ago
    video: {
      room: roomName,
      roomJoin: true,
      canPublish: true,
      canSubscribe: true,
      canPublishData: true
    }
  };

  // Encode header and payload
  const encodedHeader = arrayBufferToBase64Url(new TextEncoder().encode(JSON.stringify(header)));
  const encodedPayload = arrayBufferToBase64Url(new TextEncoder().encode(JSON.stringify(payload)));
  
  // Create signature
  const signatureInput = `${encodedHeader}.${encodedPayload}`;
  const signatureBuffer = await hmacSha256(apiSecret, signatureInput);
  const encodedSignature = arrayBufferToBase64Url(signatureBuffer);

  return `${encodedHeader}.${encodedPayload}.${encodedSignature}`;
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
    const token = await generateLiveKitToken(roomId, participantName);

    console.log(`Generated token for user: ${participantName}, room: ${roomId}`);

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
