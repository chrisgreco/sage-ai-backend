
import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.7.1';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const philosophyThemes = [
  "ancient Greek philosopher with olive wreath",
  "Socratic dialogue scene with scrolls",
  "Greek temple columns with wisdom symbols",
  "ancient amphitheater debate scene",
  "philosopher with geometric patterns",
  "Greek pottery with philosophical symbols",
  "marble bust style with laurel crown",
  "ancient Greek agora discussion",
  "philosopher under olive tree",
  "Greek geometric art with wisdom motifs"
];

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const { userId } = await req.json();
    
    if (!userId) {
      return new Response(
        JSON.stringify({ error: "User ID is required" }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
      );
    }

    const openAIApiKey = Deno.env.get('OPENAI_API_KEY');
    if (!openAIApiKey) {
      return new Response(
        JSON.stringify({ error: "OpenAI API key not configured" }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
      );
    }

    // Create deterministic theme based on user ID
    const themeIndex = userId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % philosophyThemes.length;
    const baseTheme = philosophyThemes[themeIndex];
    
    // Add unique variations based on user ID
    const variations = ["minimalist", "geometric", "classical", "modern interpretation of", "stylized"];
    const variationIndex = userId.length % variations.length;
    const variation = variations[variationIndex];
    
    const prompt = `Create a ${variation} ${baseTheme}, designed as a profile avatar. Style: clean, professional, suitable for a debate platform. Colors: sage green, gold, marble white. Circular composition, high contrast, simple but elegant. Ancient Greek philosophy theme.`;

    console.log('Making request to OpenAI with prompt:', prompt);

    const response = await fetch('https://api.openai.com/v1/images/generations', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${openAIApiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'dall-e-3',
        prompt: prompt,
        n: 1,
        size: '1024x1024',
        quality: 'standard',
        response_format: 'b64_json'
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('OpenAI API error:', response.status, errorText);
      throw new Error(`OpenAI API error: ${response.statusText} - ${errorText}`);
    }

    const data = await response.json();
    const imageData = data.data[0].b64_json;

    // Store in Supabase Storage
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    const fileName = `profile-${userId}-${Date.now()}.png`;
    const imageBuffer = Uint8Array.from(atob(imageData), c => c.charCodeAt(0));

    const { data: uploadData, error: uploadError } = await supabase.storage
      .from('avatars')
      .upload(fileName, imageBuffer, {
        contentType: 'image/png',
        upsert: false
      });

    if (uploadError) {
      console.error('Upload error:', uploadError);
      throw new Error(`Upload error: ${uploadError.message}`);
    }

    const { data: { publicUrl } } = supabase.storage
      .from('avatars')
      .getPublicUrl(fileName);

    // Update user profile with new avatar URL
    const { error: updateError } = await supabase
      .from('profiles')
      .update({ avatar_url: publicUrl })
      .eq('id', userId);

    if (updateError) {
      console.error('Profile update error:', updateError);
    }

    console.log('Successfully generated and stored profile icon:', publicUrl);

    return new Response(
      JSON.stringify({ avatar_url: publicUrl }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error) {
    console.error('Error generating profile icon:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
    );
  }
});
