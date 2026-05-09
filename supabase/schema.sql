-- RAG Electronics Recommender — custom users + chat + preferences
-- Paste into Supabase SQL Editor (or run via migration).
-- Uses custom application users (plaintext password column). Not Supabase Auth.

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- users: application accounts (not auth.users)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- chat_history: persisted turns per user
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON public.chat_history (user_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_user_timestamp ON public.chat_history (user_id, timestamp DESC);

-- ---------------------------------------------------------------------------
-- user_preferences: key/value profile for RAG personalization
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    preference_key TEXT NOT NULL,
    preference_value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, preference_key)
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON public.user_preferences (user_id);

-- ---------------------------------------------------------------------------
-- Optional RLS using a custom JWT claim `user_id` (NOT auth.uid())
-- Enable only if you mint your own JWTs and pass Authorization: Bearer <jwt>
-- from clients. Backend using the service_role key bypasses RLS.
-- Uncomment the block below to enable policies.
-- ---------------------------------------------------------------------------
-- ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.chat_history ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;
--
-- -- Example: require JWT claim user_id matching row id for users row
-- CREATE POLICY users_select_own
-- ON public.users FOR SELECT
-- USING (id::text = (auth.jwt() ->> 'user_id'));
--
-- CREATE POLICY users_update_own
-- ON public.users FOR UPDATE
-- USING (id::text = (auth.jwt() ->> 'user_id'))
-- WITH CHECK (id::text = (auth.jwt() ->> 'user_id'));
--
-- CREATE POLICY chat_history_rw_own
-- ON public.chat_history FOR ALL
-- USING (user_id::text = (auth.jwt() ->> 'user_id'))
-- WITH CHECK (user_id::text = (auth.jwt() ->> 'user_id'));
--
-- CREATE POLICY user_preferences_rw_own
-- ON public.user_preferences FOR ALL
-- USING (user_id::text = (auth.jwt() ->> 'user_id'))
-- WITH CHECK (user_id::text = (auth.jwt() ->> 'user_id'));
