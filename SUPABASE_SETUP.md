# Supabase Database Setup for LiveKit Debate Moderator

This guide helps you set up the required Supabase database schema for persistent memory features in the LiveKit Debate Moderator agent.

## 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Choose a region close to your Render deployment
3. Note down your project URL and API keys from Settings > API

## 2. Required Environment Variables

Set these in your Render service environment variables [[memory:2232389]]:

```bash
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key        # For client-side operations
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key  # For server-side operations (recommended)
```

## 3. Database Schema

Run these SQL commands in your Supabase SQL Editor:

### Create Tables

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Debate Sessions Table
CREATE TABLE public.debate_sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    room_name TEXT NOT NULL UNIQUE,
    topic TEXT NOT NULL,
    moderator_persona TEXT NOT NULL,
    participants TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'ended', 'paused'))
);

-- Conversation Turns Table
CREATE TABLE public.conversation_turns (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID REFERENCES public.debate_sessions(id) ON DELETE CASCADE,
    speaker TEXT NOT NULL,
    content TEXT NOT NULL,
    turn_type TEXT DEFAULT 'speech' CHECK (turn_type IN ('speech', 'action', 'system')),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Participant Memory Table
CREATE TABLE public.participant_memory (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID REFERENCES public.debate_sessions(id) ON DELETE CASCADE,
    participant TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Moderation Actions Table
CREATE TABLE public.moderation_actions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id UUID REFERENCES public.debate_sessions(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);
```

### Create Indexes for Performance

```sql
-- Indexes for better query performance
CREATE INDEX idx_debate_sessions_room_name ON public.debate_sessions(room_name);
CREATE INDEX idx_debate_sessions_status ON public.debate_sessions(status);
CREATE INDEX idx_conversation_turns_session_id ON public.conversation_turns(session_id);
CREATE INDEX idx_conversation_turns_timestamp ON public.conversation_turns(timestamp);
CREATE INDEX idx_participant_memory_session_id ON public.participant_memory(session_id);
CREATE INDEX idx_participant_memory_participant ON public.participant_memory(participant);
CREATE INDEX idx_moderation_actions_session_id ON public.moderation_actions(session_id);
CREATE INDEX idx_moderation_actions_timestamp ON public.moderation_actions(timestamp);
```

### Create Updated At Trigger

```sql
-- Function to automatically update updated_at timestamps
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for debate_sessions table
CREATE TRIGGER set_timestamp_debate_sessions
    BEFORE UPDATE ON public.debate_sessions
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();
```

## 4. Row Level Security (RLS)

For production security, enable RLS:

```sql
-- Enable RLS on all tables
ALTER TABLE public.debate_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.participant_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.moderation_actions ENABLE ROW LEVEL SECURITY;

-- Create policies for service role access (unrestricted for server-side operations)
CREATE POLICY "Service role can manage all debate_sessions" ON public.debate_sessions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage all conversation_turns" ON public.conversation_turns
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage all participant_memory" ON public.participant_memory
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage all moderation_actions" ON public.moderation_actions
    FOR ALL USING (auth.role() = 'service_role');

-- Create policies for anon access (read-only for debugging)
CREATE POLICY "Anon can read debate_sessions" ON public.debate_sessions
    FOR SELECT USING (true);

CREATE POLICY "Anon can read conversation_turns" ON public.conversation_turns
    FOR SELECT USING (true);
```

## 5. Test Your Setup

You can test your setup with this SQL query:

```sql
-- Test insert
INSERT INTO public.debate_sessions (room_name, topic, moderator_persona, participants)
VALUES ('test-room', 'Test Topic', 'neutral-facilitator', ARRAY['TestUser']);

-- Test select
SELECT * FROM public.debate_sessions WHERE room_name = 'test-room';

-- Clean up test data
DELETE FROM public.debate_sessions WHERE room_name = 'test-room';
```

## 6. Environment Variables in Render

In your Render service dashboard, add these environment variables:

1. Go to your service → Environment
2. Add:
   - `SUPABASE_URL`: Your project URL from Supabase Settings > API
   - `SUPABASE_SERVICE_ROLE_KEY`: Your service role key (for server operations)
   - Optionally `SUPABASE_KEY`: Your anon key (fallback)

## 7. Troubleshooting

### Connection Issues
- Verify your SUPABASE_URL is correct (should include https://)
- Check that your API keys are properly set in Render
- Ensure your Supabase project is not paused

### Permission Errors
- Use `SUPABASE_SERVICE_ROLE_KEY` for server-side operations
- Verify RLS policies allow your key to access tables
- Check that tables exist in the `public` schema

### Performance Issues
- Monitor your database usage in Supabase Dashboard
- Consider upgrading to a paid plan for production workloads
- Review and optimize your queries if needed

The agent will automatically detect and report Supabase connection status on startup. 