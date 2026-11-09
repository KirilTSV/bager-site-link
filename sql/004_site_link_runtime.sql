-- BAGER SITE LINK runtime extension for CENTRAL DATA CORE v1.0
-- Apply after Central Data Core migrations 001-003. Review in staging first.
begin;

create table if not exists public.site_link_organizations (
  id uuid primary key default gen_random_uuid(), name text not null,
  core_organization_id uuid references public.organizations(id), created_at timestamptz not null default now()
);
create table if not exists public.site_link_projects (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.site_link_organizations(id) on delete cascade,
  core_project_id uuid references public.projects(id), code text not null, name text not null, address text not null default '',
  status text not null default 'active', created_at timestamptz not null default now(), unique(organization_id,code)
);
create table if not exists public.site_link_assets (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.site_link_organizations(id),
  project_id uuid not null references public.site_link_projects(id), core_asset_id uuid references public.assets(id),
  asset_type text not null, code text not null, registration text not null default '', capacity_m3 numeric(12,3),
  status text not null default 'available', unique(project_id,code)
);
create table if not exists public.site_link_participants (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.site_link_organizations(id),
  project_id uuid not null references public.site_link_projects(id), core_user_id uuid references auth.users(id),
  display_name text not null, phone text, role text not null check(role in ('owner','dispatcher','operator','driver','site_manager','client_viewer')),
  asset_id uuid references public.site_link_assets(id), status text not null default 'active', created_at timestamptz not null default now()
);
create unique index if not exists ux_site_link_driver_asset on public.site_link_participants(asset_id) where role='driver' and status='active';
create unique index if not exists ux_site_link_operator_asset on public.site_link_participants(asset_id) where role='operator' and status='active';
create table if not exists public.site_link_sessions (
  id text primary key, participant_id uuid not null references public.site_link_participants(id) on delete cascade,
  project_id uuid not null references public.site_link_projects(id) on delete cascade, expires_at timestamptz not null, created_at timestamptz not null default now()
);
create table if not exists public.site_link_invitations (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.site_link_organizations(id),
  project_id uuid not null references public.site_link_projects(id), participant_id uuid not null references public.site_link_participants(id),
  token_hash text not null unique, expires_at timestamptz not null, revoked boolean not null default false,
  used_at timestamptz, created_at timestamptz not null default now()
);
create table if not exists public.site_link_shifts (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.site_link_organizations(id),
  project_id uuid not null references public.site_link_projects(id), participant_id uuid not null references public.site_link_participants(id),
  asset_id uuid references public.site_link_assets(id), started_at timestamptz not null default now(), ended_at timestamptz,
  status text not null default 'open' check(status in ('open','closed'))
);
create unique index if not exists ux_site_link_one_open_shift on public.site_link_shifts(participant_id) where status='open';
create table if not exists public.site_link_trips (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.site_link_organizations(id),
  project_id uuid not null references public.site_link_projects(id), truck_asset_id uuid not null references public.site_link_assets(id),
  driver_participant_id uuid not null references public.site_link_participants(id), shift_id uuid references public.site_link_shifts(id),
  trip_number integer not null, status text not null default 'queued', queued_at timestamptz, loading_started_at timestamptz,
  loaded_at timestamptz, disposal_arrived_at timestamptz, unloaded_at timestamptz, returned_at timestamptz,
  created_at timestamptz not null default now(), unique(project_id,trip_number)
);
create unique index if not exists ux_site_link_active_trip_per_truck on public.site_link_trips(truck_asset_id) where status not in ('completed','cancelled');
create table if not exists public.site_link_gps_points (
  id bigint generated always as identity primary key, organization_id uuid not null references public.site_link_organizations(id),
  project_id uuid not null references public.site_link_projects(id), participant_id uuid not null references public.site_link_participants(id),
  asset_id uuid references public.site_link_assets(id), shift_id uuid references public.site_link_shifts(id),
  latitude double precision not null check(latitude between -90 and 90), longitude double precision not null check(longitude between -180 and 180),
  accuracy_m double precision, speed_mps double precision, heading_deg double precision, recorded_at timestamptz not null,
  received_at timestamptz not null default now(), device_event_id text not null unique
);
create index if not exists site_link_gps_project_time on public.site_link_gps_points(project_id,recorded_at desc);
create table if not exists public.site_link_load_tickets (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.site_link_organizations(id),
  project_id uuid not null references public.site_link_projects(id), trip_id uuid not null unique references public.site_link_trips(id),
  truck_asset_id uuid not null references public.site_link_assets(id), excavator_asset_id uuid references public.site_link_assets(id),
  operator_participant_id uuid not null references public.site_link_participants(id), volume_m3 numeric(12,3) not null check(volume_m3>0),
  volume_basis text not null, confidence text not null default 'estimated', confirmed_by uuid references public.site_link_participants(id),
  confirmed_at timestamptz, created_at timestamptz not null default now()
);
create table if not exists public.site_link_quantities (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.site_link_organizations(id),
  project_id uuid not null references public.site_link_projects(id), trip_id uuid not null references public.site_link_trips(id),
  quantity_type text not null, quantity_value numeric(14,3) not null check(quantity_value>=0), method text not null,
  verification_status text not null default 'unverified', measured_at timestamptz not null default now()
);
create table if not exists public.site_link_events (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.site_link_organizations(id),
  project_id uuid not null references public.site_link_projects(id), participant_id uuid references public.site_link_participants(id),
  event_type text not null, entity_type text not null, entity_id text not null, payload_json text not null default '{}',
  occurred_at timestamptz not null, recorded_at timestamptz not null default now()
);
create index if not exists site_link_events_project_time on public.site_link_events(project_id,recorded_at desc);

-- Mirror GPS into the canonical Central Data Core only when explicit core mappings exist.
create or replace function app_private.site_link_mirror_gps() returns trigger
language plpgsql security definer set search_path=public,app_private,pg_temp as $$
declare v_org uuid; v_project uuid; v_asset uuid;
begin
  select so.core_organization_id, sp.core_project_id into v_org,v_project
  from public.site_link_organizations so join public.site_link_projects sp on sp.organization_id=so.id
  where so.id=new.organization_id and sp.id=new.project_id;
  select core_asset_id into v_asset from public.site_link_assets where id=new.asset_id;
  if v_org is not null and v_project is not null then
    insert into public.gps_points(organization_id,project_id,user_id,asset_id,recorded_at,received_at,location,accuracy_m,speed_mps,heading_deg,source,device_event_id)
    values(v_org,v_project,null,v_asset,new.recorded_at,new.received_at,
      ST_SetSRID(ST_MakePoint(new.longitude,new.latitude),4326)::geography,new.accuracy_m,new.speed_mps,new.heading_deg,'device_gps',new.device_event_id)
    on conflict do nothing;
  end if;
  return new;
end $$;
drop trigger if exists trg_site_link_mirror_gps on public.site_link_gps_points;
create trigger trg_site_link_mirror_gps after insert on public.site_link_gps_points
for each row execute function app_private.site_link_mirror_gps();

-- Mirror operational events into the canonical immutable event ledger when core mapping exists.
create or replace function app_private.site_link_mirror_event() returns trigger
language plpgsql security definer set search_path=public,app_private,pg_temp as $$
declare v_org uuid; v_project uuid; v_role text;
begin
  select so.core_organization_id,sp.core_project_id into v_org,v_project
  from public.site_link_organizations so join public.site_link_projects sp on sp.organization_id=so.id
  where so.id=new.organization_id and sp.id=new.project_id;
  select role into v_role from public.site_link_participants where id=new.participant_id;
  if v_org is not null and v_project is not null then
    insert into public.operational_events(organization_id,project_id,event_type,entity_type,entity_id,occurred_at,actor_user_id,actor_role,payload,source)
    values(v_org,v_project,new.event_type,'site_link_'||new.entity_type,new.entity_id,new.occurred_at,null,v_role,new.payload_json::jsonb,'app');
  end if;
  return new;
end $$;
drop trigger if exists trg_site_link_mirror_event on public.site_link_events;
create trigger trg_site_link_mirror_event after insert on public.site_link_events
for each row execute function app_private.site_link_mirror_event();

-- The runtime API is server-only. Revoke direct browser roles; grant the trusted server role
-- only the privileges required by the API. Do not expose DB credentials in JS/HTML/Viber links.
revoke all on public.site_link_organizations, public.site_link_projects, public.site_link_assets,
 public.site_link_participants, public.site_link_sessions, public.site_link_invitations, public.site_link_shifts,
 public.site_link_trips, public.site_link_gps_points, public.site_link_load_tickets, public.site_link_quantities,
 public.site_link_events from anon, authenticated;
commit;

begin;

-- Mirror trip lifecycle into canonical Central Data Core trips when asset/project mappings exist.
create or replace function app_private.site_link_mirror_trip() returns trigger
language plpgsql security definer set search_path=public,app_private,pg_temp as $$
declare v_org uuid; v_project uuid; v_truck uuid; v_driver uuid;
begin
  select so.core_organization_id,sp.core_project_id into v_org,v_project
  from public.site_link_organizations so join public.site_link_projects sp on sp.organization_id=so.id
  where so.id=new.organization_id and sp.id=new.project_id;
  select core_asset_id into v_truck from public.site_link_assets where id=new.truck_asset_id;
  select core_user_id into v_driver from public.site_link_participants where id=new.driver_participant_id;
  if v_org is not null and v_project is not null and v_truck is not null then
    if tg_op='INSERT' then
      insert into public.trips(id,organization_id,project_id,truck_asset_id,driver_user_id,trip_number,status,queued_at,loading_started_at,loaded_at,disposal_arrived_at,unloaded_at,returned_at)
      values(new.id,v_org,v_project,v_truck,v_driver,new.trip_number,new.status,new.queued_at,new.loading_started_at,new.loaded_at,new.disposal_arrived_at,new.unloaded_at,new.returned_at)
      on conflict(id) do nothing;
    else
      update public.trips set status=new.status,queued_at=new.queued_at,loading_started_at=new.loading_started_at,
        loaded_at=new.loaded_at,disposal_arrived_at=new.disposal_arrived_at,unloaded_at=new.unloaded_at,returned_at=new.returned_at,
        driver_user_id=coalesce(v_driver,driver_user_id),updated_at=now() where id=new.id;
    end if;
  end if;
  return new;
end $$;
drop trigger if exists trg_site_link_mirror_trip on public.site_link_trips;
create trigger trg_site_link_mirror_trip after insert or update on public.site_link_trips
for each row execute function app_private.site_link_mirror_trip();

-- Mirror measured load ticket to canonical load_tickets; runtime trip and core trip share UUID.
create or replace function app_private.site_link_mirror_load_ticket() returns trigger
language plpgsql security definer set search_path=public,app_private,pg_temp as $$
declare v_org uuid; v_project uuid; v_truck uuid; v_excavator uuid; v_operator uuid; v_confirmer uuid;
begin
  select so.core_organization_id,sp.core_project_id into v_org,v_project
  from public.site_link_organizations so join public.site_link_projects sp on sp.organization_id=so.id
  where so.id=new.organization_id and sp.id=new.project_id;
  select core_asset_id into v_truck from public.site_link_assets where id=new.truck_asset_id;
  select core_asset_id into v_excavator from public.site_link_assets where id=new.excavator_asset_id;
  select core_user_id into v_operator from public.site_link_participants where id=new.operator_participant_id;
  select core_user_id into v_confirmer from public.site_link_participants where id=new.confirmed_by;
  if v_org is not null and v_project is not null and v_truck is not null
     and exists(select 1 from public.trips where id=new.trip_id) then
    insert into public.load_tickets(id,organization_id,project_id,trip_id,excavator_asset_id,operator_user_id,volume_m3,volume_basis,confirmed_by,confirmed_at,confidence,notes)
    values(new.id,v_org,v_project,new.trip_id,v_excavator,v_operator,new.volume_m3,
      case when new.volume_basis in ('truck_body_estimate','operator_estimate','survey_measurement','weighbridge_conversion','other') then new.volume_basis else 'other' end,
      v_confirmer,new.confirmed_at,new.confidence,'Mirrored from BAGER SITE LINK runtime')
    on conflict(id) do nothing;
  end if;
  return new;
end $$;
drop trigger if exists trg_site_link_mirror_load_ticket on public.site_link_load_tickets;
create trigger trg_site_link_mirror_load_ticket after insert on public.site_link_load_tickets
for each row execute function app_private.site_link_mirror_load_ticket();

-- Mirror loaded quantity with an explicit method mapping to the Core Data Core enum/check set.
create or replace function app_private.site_link_mirror_quantity() returns trigger
language plpgsql security definer set search_path=public,app_private,pg_temp as $$
declare v_org uuid; v_project uuid; v_measurer uuid; v_verifier uuid;
begin
  select so.core_organization_id,sp.core_project_id into v_org,v_project
  from public.site_link_organizations so join public.site_link_projects sp on sp.organization_id=so.id
  where so.id=new.organization_id and sp.id=new.project_id;
  select core_user_id into v_measurer from public.site_link_participants p join public.site_link_load_tickets t on t.operator_participant_id=p.id where t.trip_id=new.trip_id limit 1;
  select core_user_id into v_verifier from public.site_link_participants p join public.site_link_load_tickets t on t.confirmed_by=p.id where t.trip_id=new.trip_id limit 1;
  if v_org is not null and v_project is not null then
    insert into public.quantity_measurements(id,organization_id,project_id,quantity_type,quantity_value,measurement_method,measured_by,verified_by,verification_status,measured_at,notes)
    values(new.id,v_org,v_project,new.quantity_type,new.quantity_value,
      case when new.method in ('trip_sum','survey','weighbridge','machine_counter','manual_measurement','engineer_certificate','other') then new.method else 'manual_measurement' end,
      v_measurer,v_verifier,
      case when new.verification_status in ('unverified','verified','disputed','rejected') then new.verification_status else 'unverified' end,
      new.measured_at,'Mirrored from BAGER SITE LINK runtime')
    on conflict(id) do nothing;
  end if;
  return new;
end $$;
drop trigger if exists trg_site_link_mirror_quantity on public.site_link_quantities;
create trigger trg_site_link_mirror_quantity after insert on public.site_link_quantities
for each row execute function app_private.site_link_mirror_quantity();
commit;
