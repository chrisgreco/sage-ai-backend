-- Debate Memory System Migration
-- Stores conversation memory and context for AI debate rooms

-- Create debate_rooms table to track active/past debates
CREATE TABLE public.debate_rooms (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  room_name TEXT NOT NULL UNIQUE,
  debate_topic TEXT NOT NULL,
  livekit_token_hash TEXT NOT NULL, -- Hash of the LiveKit token for security
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed')),
  participants JSONB DEFAULT '[]'::jsonb, -- Array of participant info
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  session_count INTEGER DEFAULT 1, -- Track session resets (every 30min)
  total_duration_minutes INTEGER DEFAULT 0
);

-- Create conversation_memory table for storing debate segments
CREATE TABLE public.conversation_memory (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  room_id UUID NOT NULL REFERENCES public.debate_rooms(id) ON DELETE CASCADE,
  session_number INTEGER NOT NULL DEFAULT 1, -- Which 30-min session this belongs to
  segment_number INTEGER NOT NULL DEFAULT 1, -- Chronological order within session
  speaker_role TEXT NOT NULL, -- 'human', 'socrates', 'aristotle', 'buddha', 'hermes', 'solon'
  speaker_name TEXT, -- Human participant name or AI personality
  content_text TEXT, -- Transcribed text content
  content_summary TEXT, -- AI-generated summary for compression
  key_points JSONB DEFAULT '[]'::jsonb, -- Extracted important points
  references_to JSONB DEFAULT '[]'::jsonb, -- What previous points this references
  timestamp_start TIMESTAMP WITH TIME ZONE NOT NULL,
  timestamp_end TIMESTAMP WITH TIME ZONE,
  token_count INTEGER DEFAULT 0,
  is_compressed BOOLEAN DEFAULT false, -- Whether this has been summarized
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create debate_context table for session-level summaries
CREATE TABLE public.debate_context (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  room_id UUID NOT NULL REFERENCES public.debate_rooms(id) ON DELETE CASCADE,
  session_number INTEGER NOT NULL,
  context_type TEXT NOT NULL CHECK (context_type IN ('session_summary', 'key_arguments', 'personality_stances', 'unresolved_questions')),
  content TEXT NOT NULL,
  ai_personalities_mentioned JSONB DEFAULT '[]'::jsonb,
  human_participants_mentioned JSONB DEFAULT '[]'::jsonb,
  importance_score INTEGER DEFAULT 5 CHECK (importance_score BETWEEN 1 AND 10),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create personality_memory table for AI agent-specific memory
CREATE TABLE public.personality_memory (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  room_id UUID NOT NULL REFERENCES public.debate_rooms(id) ON DELETE CASCADE,
  personality TEXT NOT NULL CHECK (personality IN ('socrates', 'aristotle', 'buddha', 'hermes', 'solon')),
  memory_type TEXT NOT NULL CHECK (memory_type IN ('key_question', 'stance_taken', 'insight_shared', 'moderation_action')),
  content TEXT NOT NULL,
  related_to_segment_id UUID REFERENCES public.conversation_memory(id),
  session_number INTEGER NOT NULL,
  relevance_score INTEGER DEFAULT 5 CHECK (relevance_score BETWEEN 1 AND 10),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Enable Row Level Security on all tables
ALTER TABLE public.debate_rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.debate_context ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.personality_memory ENABLE ROW LEVEL SECURITY;

-- Create policies for debate_rooms (accessible by room token holders)
CREATE POLICY "Debate rooms are viewable by token holders" 
  ON public.debate_rooms 
  FOR SELECT 
  USING (true); -- We'll handle token validation in the backend

CREATE POLICY "Debate rooms can be created by authenticated users" 
  ON public.debate_rooms 
  FOR INSERT 
  WITH CHECK (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Debate rooms can be updated" 
  ON public.debate_rooms 
  FOR UPDATE 
  USING (true); -- Backend will validate token access

-- Create policies for conversation_memory
CREATE POLICY "Conversation memory is viewable for room participants" 
  ON public.conversation_memory 
  FOR SELECT 
  USING (true);

CREATE POLICY "Conversation memory can be inserted by system" 
  ON public.conversation_memory 
  FOR INSERT 
  WITH CHECK (true);

CREATE POLICY "Conversation memory can be updated for compression" 
  ON public.conversation_memory 
  FOR UPDATE 
  USING (true);

-- Create policies for debate_context
CREATE POLICY "Debate context is viewable for room participants" 
  ON public.debate_context 
  FOR SELECT 
  USING (true);

CREATE POLICY "Debate context can be managed by system" 
  ON public.debate_context 
  FOR ALL 
  USING (true);

-- Create policies for personality_memory
CREATE POLICY "Personality memory is viewable for room participants" 
  ON public.personality_memory 
  FOR SELECT 
  USING (true);

CREATE POLICY "Personality memory can be managed by system" 
  ON public.personality_memory 
  FOR ALL 
  USING (true);

-- Create indexes for performance
CREATE INDEX idx_debate_rooms_token_hash ON public.debate_rooms(livekit_token_hash);
CREATE INDEX idx_debate_rooms_room_name ON public.debate_rooms(room_name);
CREATE INDEX idx_conversation_memory_room_session ON public.conversation_memory(room_id, session_number, segment_number);
CREATE INDEX idx_conversation_memory_speaker ON public.conversation_memory(speaker_role, speaker_name);
CREATE INDEX idx_conversation_memory_timestamp ON public.conversation_memory(timestamp_start);
CREATE INDEX idx_debate_context_room_session ON public.debate_context(room_id, session_number, context_type);
CREATE INDEX idx_personality_memory_room_personality ON public.personality_memory(room_id, personality, session_number);

-- Create functions for memory management
CREATE OR REPLACE FUNCTION public.get_room_context(
  p_room_name TEXT,
  p_session_number INTEGER DEFAULT NULL
)
RETURNS TABLE (
  context_type TEXT,
  content TEXT,
  session_number INTEGER,
  importance_score INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    dc.context_type,
    dc.content,
    dc.session_number,
    dc.importance_score
  FROM public.debate_context dc
  JOIN public.debate_rooms dr ON dc.room_id = dr.id
  WHERE dr.room_name = p_room_name
    AND (p_session_number IS NULL OR dc.session_number = p_session_number)
  ORDER BY dc.importance_score DESC, dc.updated_at DESC;
END;
$$;

CREATE OR REPLACE FUNCTION public.get_personality_memory(
  p_room_name TEXT,
  p_personality TEXT,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  memory_type TEXT,
  content TEXT,
  session_number INTEGER,
  relevance_score INTEGER,
  created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    pm.memory_type,
    pm.content,
    pm.session_number,
    pm.relevance_score,
    pm.created_at
  FROM public.personality_memory pm
  JOIN public.debate_rooms dr ON pm.room_id = dr.id
  WHERE dr.room_name = p_room_name
    AND pm.personality = p_personality
  ORDER BY pm.relevance_score DESC, pm.created_at DESC
  LIMIT p_limit;
END;
$$;

-- Create function to compress old conversation memory
CREATE OR REPLACE FUNCTION public.compress_old_memory(
  p_room_id UUID,
  p_session_number INTEGER,
  p_keep_last_segments INTEGER DEFAULT 5
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  segments_compressed INTEGER := 0;
  segment_record RECORD;
BEGIN
  -- Compress segments older than the last N segments
  FOR segment_record IN 
    SELECT id, content_text, speaker_role, speaker_name
    FROM public.conversation_memory
    WHERE room_id = p_room_id 
      AND session_number = p_session_number
      AND is_compressed = false
      AND segment_number <= (
        SELECT MAX(segment_number) - p_keep_last_segments
        FROM public.conversation_memory
        WHERE room_id = p_room_id AND session_number = p_session_number
      )
    ORDER BY segment_number
  LOOP
    -- Create summary (simplified - in real implementation, call AI for summarization)
    UPDATE public.conversation_memory
    SET 
      content_summary = LEFT(segment_record.content_text, 200) || '...',
      is_compressed = true,
      content_text = NULL -- Clear full text to save space
    WHERE id = segment_record.id;
    
    segments_compressed := segments_compressed + 1;
  END LOOP;
  
  RETURN segments_compressed;
END;
$$; 