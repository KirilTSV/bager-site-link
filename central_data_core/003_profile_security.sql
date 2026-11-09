-- Additional profile protection. Apply after 001 and 002.
begin;
alter table public.user_profiles enable row level security;
drop policy if exists profile_self_read on public.user_profiles;
create policy profile_self_read on public.user_profiles for select using (user_id = auth.uid());
drop policy if exists profile_self_insert on public.user_profiles;
create policy profile_self_insert on public.user_profiles for insert with check (user_id = auth.uid());
drop policy if exists profile_self_update on public.user_profiles;
create policy profile_self_update on public.user_profiles for update using (user_id = auth.uid()) with check (user_id = auth.uid());
commit;
