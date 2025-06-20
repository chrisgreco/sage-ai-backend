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

-- Create knowledge_documents table for AI agent knowledge base
CREATE TABLE public.knowledge_documents (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_name TEXT NOT NULL CHECK (agent_name IN ('aristotle', 'socrates', 'hermes', 'buddha')),
  document_name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  content_text TEXT NOT NULL,
  summary TEXT,
  document_type TEXT DEFAULT 'pdf' CHECK (document_type IN ('pdf', 'text', 'markdown')),
  keywords JSONB DEFAULT '[]'::jsonb, -- Searchable keywords
  chapter_sections JSONB DEFAULT '[]'::jsonb, -- Document structure
  file_size_bytes INTEGER DEFAULT 0,
  page_count INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  UNIQUE(agent_name, document_name)
);

-- Create knowledge_chunks table for semantic search
CREATE TABLE public.knowledge_chunks (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  document_id UUID NOT NULL REFERENCES public.knowledge_documents(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  chunk_summary TEXT,
  context_keywords JSONB DEFAULT '[]'::jsonb,
  chunk_size INTEGER NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  UNIQUE(document_id, chunk_index)
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
ALTER TABLE public.knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_chunks ENABLE ROW LEVEL SECURITY;
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

-- Create policies for knowledge_documents (readable by service role and authenticated users)
CREATE POLICY "Knowledge documents are viewable" 
  ON public.knowledge_documents 
  FOR SELECT 
  USING (true);

CREATE POLICY "Knowledge documents can be managed by service role" 
  ON public.knowledge_documents 
  FOR ALL 
  USING (auth.role() = 'service_role');

-- Create policies for knowledge_chunks (readable by service role and authenticated users)
CREATE POLICY "Knowledge chunks are viewable" 
  ON public.knowledge_chunks 
  FOR SELECT 
  USING (true);

CREATE POLICY "Knowledge chunks can be managed by service role" 
  ON public.knowledge_chunks 
  FOR ALL 
  USING (auth.role() = 'service_role');

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

-- Knowledge base indexes
CREATE INDEX idx_knowledge_documents_agent ON public.knowledge_documents(agent_name);
CREATE INDEX idx_knowledge_documents_name ON public.knowledge_documents(document_name);
CREATE INDEX idx_knowledge_chunks_document ON public.knowledge_chunks(document_id, chunk_index);
CREATE INDEX idx_knowledge_chunks_keywords ON public.knowledge_chunks USING GIN (context_keywords);

-- Memory indexes
CREATE INDEX idx_conversation_memory_room_session ON public.conversation_memory(room_id, session_number, segment_number);
CREATE INDEX idx_conversation_memory_speaker ON public.conversation_memory(speaker_role, speaker_name);
CREATE INDEX idx_conversation_memory_timestamp ON public.conversation_memory(timestamp_start);
CREATE INDEX idx_debate_context_room_session ON public.debate_context(room_id, session_number, context_type);
CREATE INDEX idx_personality_memory_room_personality ON public.personality_memory(room_id, personality, session_number);

-- Create functions for knowledge base operations
CREATE OR REPLACE FUNCTION public.search_agent_knowledge(
  p_agent_name TEXT,
  p_search_terms TEXT[],
  p_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
  document_name TEXT,
  chunk_text TEXT,
  chunk_summary TEXT,
  relevance_score NUMERIC
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    kd.document_name,
    kc.chunk_text,
    kc.chunk_summary,
    (
      -- Simple keyword matching score
      CASE 
        WHEN array_length(p_search_terms, 1) IS NULL THEN 0
        ELSE (
          SELECT COUNT(*)::NUMERIC 
          FROM unnest(p_search_terms) AS term
          WHERE kc.chunk_text ILIKE '%' || term || '%' 
             OR kc.chunk_summary ILIKE '%' || term || '%'
             OR kd.summary ILIKE '%' || term || '%'
        ) / array_length(p_search_terms, 1)
      END
    ) AS relevance_score
  FROM public.knowledge_chunks kc
  JOIN public.knowledge_documents kd ON kc.document_id = kd.id
  WHERE kd.agent_name = p_agent_name
    AND (
      array_length(p_search_terms, 1) IS NULL 
      OR EXISTS (
        SELECT 1 FROM unnest(p_search_terms) AS term
        WHERE kc.chunk_text ILIKE '%' || term || '%' 
           OR kc.chunk_summary ILIKE '%' || term || '%'
           OR kd.summary ILIKE '%' || term || '%'
      )
    )
  ORDER BY relevance_score DESC, kc.chunk_index ASC
  LIMIT p_limit;
END;
$$;

-- Create function to store knowledge documents
CREATE OR REPLACE FUNCTION public.upsert_knowledge_document(
  p_agent_name TEXT,
  p_document_name TEXT,
  p_file_path TEXT,
  p_content_text TEXT,
  p_summary TEXT DEFAULT NULL,
  p_document_type TEXT DEFAULT 'pdf',
  p_keywords JSONB DEFAULT '[]'::jsonb,
  p_file_size_bytes INTEGER DEFAULT 0,
  p_page_count INTEGER DEFAULT 0
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_document_id UUID;
BEGIN
  -- Insert or update knowledge document
  INSERT INTO public.knowledge_documents (
    agent_name, document_name, file_path, content_text, summary, 
    document_type, keywords, file_size_bytes, page_count, updated_at
  ) VALUES (
    p_agent_name, p_document_name, p_file_path, p_content_text, p_summary,
    p_document_type, p_keywords, p_file_size_bytes, p_page_count, NOW()
  )
  ON CONFLICT (agent_name, document_name) 
  DO UPDATE SET 
    file_path = EXCLUDED.file_path,
    content_text = EXCLUDED.content_text,
    summary = EXCLUDED.summary,
    document_type = EXCLUDED.document_type,
    keywords = EXCLUDED.keywords,
    file_size_bytes = EXCLUDED.file_size_bytes,
    page_count = EXCLUDED.page_count,
    updated_at = NOW()
  RETURNING id INTO v_document_id;
  
  RETURN v_document_id;
END;
$$;

-- Create function to store knowledge chunks
CREATE OR REPLACE FUNCTION public.store_knowledge_chunks(
  p_document_id UUID,
  p_chunks JSONB
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_chunk JSONB;
  v_inserted_count INTEGER := 0;
BEGIN
  -- Clear existing chunks for this document
  DELETE FROM public.knowledge_chunks WHERE document_id = p_document_id;
  
  -- Insert new chunks
  FOR v_chunk IN SELECT jsonb_array_elements(p_chunks)
  LOOP
    INSERT INTO public.knowledge_chunks (
      document_id, chunk_index, chunk_text, chunk_summary, 
      context_keywords, chunk_size
    ) VALUES (
      p_document_id,
      (v_chunk->>'chunk_index')::INTEGER,
      v_chunk->>'chunk_text',
      v_chunk->>'chunk_summary',
      COALESCE(v_chunk->'context_keywords', '[]'::jsonb),
      length(v_chunk->>'chunk_text')
    );
    
    v_inserted_count := v_inserted_count + 1;
  END LOOP;
  
  RETURN v_inserted_count;
END;
$$;

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