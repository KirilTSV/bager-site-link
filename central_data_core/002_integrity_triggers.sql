-- BAGER SYSTEM integrity layer v1.0
-- Apply only after 001_core_schema.sql in a Supabase/PostgreSQL staging project.
begin;

create or replace function app_private.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

do $$
declare t text;
begin
  foreach t in array array['organizations','user_profiles','business_parties','projects','assets','trips'] loop
    execute format('drop trigger if exists trg_%I_updated_at on public.%I', t, t);
    execute format('create trigger trg_%I_updated_at before update on public.%I for each row execute function app_private.set_updated_at()', t, t);
  end loop;
end $$;

-- Operational event ledger is append-only. Corrections are new events, not edits.
create or replace function app_private.reject_ledger_mutation()
returns trigger language plpgsql as $$
begin
  raise exception 'This ledger is append-only; create a correction event instead.';
end;
$$;
drop trigger if exists trg_operational_events_immutable on public.operational_events;
create trigger trg_operational_events_immutable
before update or delete on public.operational_events
for each row execute function app_private.reject_ledger_mutation();
drop trigger if exists trg_audit_log_immutable on public.audit_log;
create trigger trg_audit_log_immutable
before update or delete on public.audit_log
for each row execute function app_private.reject_ledger_mutation();

-- Generic audit capture for selected mutable business tables.
create or replace function app_private.capture_audit()
returns trigger language plpgsql security definer set search_path = public, app_private, pg_temp as $$
declare
  v_old jsonb;
  v_new jsonb;
  v_org uuid;
  v_project uuid;
  v_id text;
begin
  if tg_op <> 'INSERT' then v_old := to_jsonb(old); end if;
  if tg_op <> 'DELETE' then v_new := to_jsonb(new); end if;
  v_org := coalesce((v_new->>'organization_id')::uuid,(v_old->>'organization_id')::uuid);
  v_project := coalesce((v_new->>'project_id')::uuid,(v_old->>'project_id')::uuid);
  v_id := coalesce(v_new->>'id',v_old->>'id');
  insert into public.audit_log(organization_id,project_id,actor_user_id,action,table_name,record_id,before_data,after_data)
  values (v_org,v_project,auth.uid(),tg_op,tg_table_name,v_id,v_old,v_new);
  if tg_op = 'DELETE' then return old; else return new; end if;
end;
$$;

do $$
declare t text;
begin
  foreach t in array array[
    'business_parties','projects','assets','project_assignments','shifts','trips','load_tickets',
    'quantity_measurements','cost_entries','revenue_entries','cash_movements','cameras','media_objects'
  ] loop
    execute format('drop trigger if exists trg_%I_audit on public.%I', t, t);
    execute format('create trigger trg_%I_audit after insert or update or delete on public.%I for each row execute function app_private.capture_audit()', t, t);
  end loop;
end $$;

-- Important: audit rows are written by a SECURITY DEFINER trigger. The function owner
-- must have INSERT rights on audit_log. Do not grant clients direct UPDATE/DELETE on audit_log.

commit;
