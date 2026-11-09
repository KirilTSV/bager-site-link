-- BAGER SYSTEM CENTRAL DATA CORE v1.0
-- PostgreSQL 15+ / Supabase-compatible starting migration.
-- Review in staging before production. Requires PostGIS and pgcrypto.

begin;
create extension if not exists pgcrypto;
create extension if not exists postgis;

create schema if not exists app_private;

-- ---------- ENUM-LIKE CHECKED TEXT ----------
-- Text + CHECK constraints are intentionally used for easier future migrations.

-- ---------- ORGANIZATIONS / IDENTITY ----------
create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  legal_name text not null,
  display_name text not null,
  vat_number text,
  country_code char(2) not null default 'BG',
  default_currency char(3) not null default 'EUR' check (default_currency = 'EUR'),
  timezone text not null default 'Europe/Sofia',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.user_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  full_name text,
  phone_e164 text,
  preferred_language text not null default 'bg',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.organization_memberships (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('owner','admin','dispatcher','site_manager','operator','driver','finance','client_viewer','auditor')),
  status text not null default 'active' check (status in ('invited','active','suspended','removed')),
  created_at timestamptz not null default now(),
  unique (organization_id,user_id)
);
create index if not exists ix_memberships_user on public.organization_memberships(user_id, status);

create table if not exists public.invitations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid,
  invited_phone_e164 text,
  invited_email text,
  role text not null check (role in ('dispatcher','site_manager','operator','driver','client_viewer','auditor')),
  token_hash text not null unique,
  verification_code_hash text,
  expires_at timestamptz not null,
  max_uses integer not null default 1 check (max_uses between 1 and 20),
  use_count integer not null default 0 check (use_count >= 0),
  revoked_at timestamptz,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now()
);

-- ---------- CLIENTS / PARTNERS ----------
create table if not exists public.business_parties (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  party_type text not null check (party_type in ('client','subcontractor','supplier','disposal_site','carrier','other')),
  legal_name text not null,
  display_name text,
  vat_number text,
  contact_name text,
  phone_e164 text,
  email text,
  address text,
  notes text,
  status text not null default 'active' check (status in ('active','inactive','blocked')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id,id)
);
create index if not exists ix_parties_org_type on public.business_parties(organization_id,party_type,status);

-- ---------- PROJECTS / SITES ----------
create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_code text not null,
  name text not null,
  client_party_id uuid,
  site_address text,
  site_location geography(point,4326),
  planned_start date,
  planned_end date,
  actual_start timestamptz,
  actual_end timestamptz,
  status text not null default 'lead' check (status in ('lead','quoted','approved','scheduled','active','paused','completed','cancelled','archived')),
  contract_currency char(3) not null default 'EUR' check (contract_currency = 'EUR'),
  notes text,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id,project_code),
  unique (organization_id,id),
  foreign key (organization_id,client_party_id) references public.business_parties(organization_id,id)
);
create index if not exists ix_projects_org_status on public.projects(organization_id,status,planned_start);
create index if not exists ix_projects_location on public.projects using gist(site_location);

create table if not exists public.site_zones (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid not null,
  name text not null,
  zone_type text not null check (zone_type in ('work_area','loading','unloading','parking','restricted','access_road','other')),
  boundary geography(polygon,4326),
  center geography(point,4326),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  foreign key (organization_id,project_id) references public.projects(organization_id,id) on delete cascade
);
create index if not exists ix_site_zones_boundary on public.site_zones using gist(boundary);

-- ---------- ASSETS / PEOPLE / ASSIGNMENTS ----------
create table if not exists public.assets (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  owner_party_id uuid,
  asset_type text not null check (asset_type in ('tracked_excavator','backhoe_loader','dump_truck','roller','loader','lowbed','camera','other')),
  internal_code text,
  registration_number text,
  make text,
  model text,
  capacity_m3 numeric(12,3),
  payload_t numeric(12,3),
  serial_number text,
  status text not null default 'available' check (status in ('available','assigned','maintenance','inactive','retired')),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id,id),
  foreign key (organization_id,owner_party_id) references public.business_parties(organization_id,id)
);
create index if not exists ix_assets_org_type_status on public.assets(organization_id,asset_type,status);
create unique index if not exists ux_assets_registration on public.assets(organization_id,registration_number) where registration_number is not null;

create table if not exists public.project_assignments (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid not null,
  asset_id uuid,
  user_id uuid references auth.users(id),
  party_id uuid,
  assignment_role text not null check (assignment_role in ('operator','driver','machine','truck','site_manager','subcontractor','dispatcher')),
  starts_at timestamptz not null,
  ends_at timestamptz,
  status text not null default 'planned' check (status in ('planned','active','ended','cancelled')),
  created_at timestamptz not null default now(),
  foreign key (organization_id,project_id) references public.projects(organization_id,id) on delete cascade,
  foreign key (organization_id,asset_id) references public.assets(organization_id,id),
  foreign key (organization_id,party_id) references public.business_parties(organization_id,id),
  check (ends_at is null or ends_at > starts_at)
);
create index if not exists ix_assignments_project_time on public.project_assignments(project_id,starts_at,ends_at);
create index if not exists ix_assignments_asset_time on public.project_assignments(asset_id,starts_at,ends_at);

create table if not exists public.shifts (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid not null,
  user_id uuid not null references auth.users(id),
  asset_id uuid,
  role text not null check (role in ('operator','driver','site_manager','dispatcher')),
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  start_location geography(point,4326),
  end_location geography(point,4326),
  start_meter numeric(14,2),
  end_meter numeric(14,2),
  status text not null default 'open' check (status in ('open','closed','voided')),
  created_at timestamptz not null default now(),
  foreign key (organization_id,project_id) references public.projects(organization_id,id) on delete cascade,
  foreign key (organization_id,asset_id) references public.assets(organization_id,id),
  check (ended_at is null or ended_at >= started_at)
);
create index if not exists ix_shifts_project_start on public.shifts(project_id,started_at desc);
create index if not exists ix_shifts_user_open on public.shifts(user_id,status);

-- ---------- GPS / TELEMETRY ----------
create table if not exists public.gps_points (
  id bigint generated always as identity primary key,
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid not null,
  shift_id uuid,
  user_id uuid references auth.users(id),
  asset_id uuid,
  recorded_at timestamptz not null,
  received_at timestamptz not null default now(),
  location geography(point,4326) not null,
  accuracy_m numeric(8,2),
  speed_mps numeric(8,2),
  heading_deg numeric(6,2),
  altitude_m numeric(9,2),
  source text not null default 'device_gps' check (source in ('device_gps','vehicle_telematics','manual')),
  is_mock_suspected boolean not null default false,
  device_event_id text,
  foreign key (organization_id,project_id) references public.projects(organization_id,id) on delete cascade,
  foreign key (shift_id) references public.shifts(id) on delete set null,
  foreign key (organization_id,asset_id) references public.assets(organization_id,id)
);
create index if not exists ix_gps_project_recorded on public.gps_points(project_id,recorded_at desc);
create index if not exists ix_gps_location on public.gps_points using gist(location);
create unique index if not exists ux_gps_device_event on public.gps_points(organization_id,device_event_id) where device_event_id is not null;

-- ---------- TRIPS / LOADS / QUANTITY EVIDENCE ----------
create table if not exists public.trips (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid not null,
  truck_asset_id uuid not null,
  driver_user_id uuid references auth.users(id),
  shift_id uuid references public.shifts(id),
  disposal_party_id uuid,
  trip_number integer,
  status text not null default 'created' check (status in ('created','queued','loading','loaded','outbound','at_disposal','unloading','returning','completed','cancelled','disputed')),
  queued_at timestamptz,
  loading_started_at timestamptz,
  loaded_at timestamptz,
  disposal_arrived_at timestamptz,
  unloaded_at timestamptz,
  returned_at timestamptz,
  route_start geography(point,4326),
  route_end geography(point,4326),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (organization_id,project_id) references public.projects(organization_id,id) on delete cascade,
  foreign key (organization_id,truck_asset_id) references public.assets(organization_id,id),
  foreign key (organization_id,disposal_party_id) references public.business_parties(organization_id,id)
);
create index if not exists ix_trips_project_status on public.trips(project_id,status,created_at desc);
create index if not exists ix_trips_truck on public.trips(truck_asset_id,created_at desc);

create table if not exists public.load_tickets (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid not null,
  trip_id uuid not null unique references public.trips(id) on delete cascade,
  excavator_asset_id uuid,
  operator_user_id uuid references auth.users(id),
  material_code text,
  volume_m3 numeric(12,3),
  volume_basis text not null check (volume_basis in ('truck_body_estimate','operator_estimate','survey_measurement','weighbridge_conversion','other')),
  fill_fraction numeric(5,4) check (fill_fraction is null or fill_fraction between 0 and 2),
  gross_weight_t numeric(12,3),
  tare_weight_t numeric(12,3),
  density_t_per_m3 numeric(12,5),
  confirmed_by uuid references auth.users(id),
  confirmed_at timestamptz,
  confidence text not null default 'unverified' check (confidence in ('unverified','estimated','confirmed','disputed','rejected')),
  notes text,
  created_at timestamptz not null default now(),
  foreign key (organization_id,project_id) references public.projects(organization_id,id) on delete cascade,
  foreign key (organization_id,excavator_asset_id) references public.assets(organization_id,id),
  check (volume_m3 is null or volume_m3 >= 0),
  check (gross_weight_t is null or tare_weight_t is null or gross_weight_t >= tare_weight_t)
);
create index if not exists ix_load_tickets_project on public.load_tickets(project_id,created_at desc);

create table if not exists public.quantity_measurements (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid not null,
  measured_at timestamptz not null default now(),
  quantity_type text not null check (quantity_type in ('in_situ_excavated_m3','loose_loaded_m3','transported_m3','disposed_m3','accepted_m3','surveyed_m3','weighed_t')),
  quantity_value numeric(14,3) not null check (quantity_value >= 0),
  measurement_method text not null check (measurement_method in ('trip_sum','survey','weighbridge','machine_counter','manual_measurement','engineer_certificate','other')),
  source_load_ticket_id uuid references public.load_tickets(id),
  measured_by uuid references auth.users(id),
  verified_by uuid references auth.users(id),
  verification_status text not null default 'unverified' check (verification_status in ('unverified','verified','disputed','rejected')),
  notes text,
  created_at timestamptz not null default now(),
  foreign key (organization_id,project_id) references public.projects(organization_id,id) on delete cascade
);
create index if not exists ix_quantities_project_type_time on public.quantity_measurements(project_id,quantity_type,measured_at desc);

-- ---------- EVENT LEDGER / AUDIT ----------
create table if not exists public.operational_events (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid not null,
  event_type text not null,
  entity_type text not null,
  entity_id text not null,
  occurred_at timestamptz not null,
  recorded_at timestamptz not null default now(),
  actor_user_id uuid references auth.users(id),
  actor_role text,
  location geography(point,4326),
  payload jsonb not null default '{}'::jsonb,
  idempotency_key text,
  source text not null default 'app' check (source in ('app','web','device','integration','system','import')),
  foreign key (organization_id,project_id) references public.projects(organization_id,id) on delete cascade,
  unique (organization_id,idempotency_key)
);
create index if not exists ix_events_project_time on public.operational_events(project_id,occurred_at desc);
create index if not exists ix_events_entity on public.operational_events(entity_type,entity_id,occurred_at desc);
create index if not exists ix_events_payload on public.operational_events using gin(payload);

create table if not exists public.audit_log (
  id bigint generated always as identity primary key,
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid,
  actor_user_id uuid references auth.users(id),
  action text not null,
  table_name text not null,
  record_id text,
  before_data jsonb,
  after_data jsonb,
  reason text,
  occurred_at timestamptz not null default now(),
  request_id text
);
create index if not exists ix_audit_org_time on public.audit_log(organization_id,occurred_at desc);

-- ---------- CAMERAS / MEDIA / DOCUMENTS ----------
create table if not exists public.cameras (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid not null,
  asset_id uuid,
  name text not null,
  camera_type text not null check (camera_type in ('fixed_ip','mobile_phone','vehicle_camera','other')),
  location geography(point,4326),
  stream_provider text,
  stream_reference_secret text,
  status text not null default 'inactive' check (status in ('active','inactive','fault','maintenance')),
  retention_days integer not null default 30 check (retention_days between 1 and 365),
  created_at timestamptz not null default now(),
  foreign key (organization_id,project_id) references public.projects(organization_id,id) on delete cascade,
  foreign key (organization_id,asset_id) references public.assets(organization_id,id)
);

create table if not exists public.media_objects (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid not null,
  camera_id uuid references public.cameras(id),
  captured_by uuid references auth.users(id),
  media_type text not null check (media_type in ('photo','video_clip','document','audio','other')),
  storage_bucket text not null,
  storage_key text not null,
  mime_type text,
  file_size_bytes bigint check (file_size_bytes is null or file_size_bytes >= 0),
  sha256_hex text,
  captured_at timestamptz,
  uploaded_at timestamptz not null default now(),
  linked_entity_type text,
  linked_entity_id text,
  visibility text not null default 'internal' check (visibility in ('internal','client_shared','restricted')),
  retention_until timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  foreign key (organization_id,project_id) references public.projects(organization_id,id) on delete cascade,
  unique (storage_bucket,storage_key)
);
create index if not exists ix_media_project_time on public.media_objects(project_id,uploaded_at desc);

-- ---------- FINANCE ----------
create table if not exists public.cost_entries (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid not null,
  party_id uuid,
  asset_id uuid,
  cost_category text not null check (cost_category in ('machine_rent','operator','truck','transport','disposal','fuel','repair','materials','labor','other')),
  description text not null,
  quantity numeric(14,3),
  unit text,
  unit_price_eur numeric(14,4),
  net_amount_eur numeric(14,2) not null check (net_amount_eur >= 0),
  vat_rate numeric(5,4) not null default 0 check (vat_rate between 0 and 1),
  vat_amount_eur numeric(14,2) not null default 0 check (vat_amount_eur >= 0),
  gross_amount_eur numeric(14,2) not null check (gross_amount_eur >= 0),
  incurred_at date not null default current_date,
  invoice_reference text,
  payment_status text not null default 'unpaid' check (payment_status in ('unpaid','part_paid','paid','disputed','voided')),
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  foreign key (organization_id,project_id) references public.projects(organization_id,id) on delete cascade,
  foreign key (organization_id,party_id) references public.business_parties(organization_id,id),
  foreign key (organization_id,asset_id) references public.assets(organization_id,id)
);
create index if not exists ix_cost_project_date on public.cost_entries(project_id,incurred_at desc);

create table if not exists public.revenue_entries (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid not null,
  client_party_id uuid,
  description text not null,
  net_amount_eur numeric(14,2) not null check (net_amount_eur >= 0),
  vat_rate numeric(5,4) not null default 0 check (vat_rate between 0 and 1),
  vat_amount_eur numeric(14,2) not null default 0 check (vat_amount_eur >= 0),
  gross_amount_eur numeric(14,2) not null check (gross_amount_eur >= 0),
  invoice_reference text,
  issued_at date,
  due_at date,
  payment_status text not null default 'unpaid' check (payment_status in ('unpaid','part_paid','paid','overdue','disputed','voided')),
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  foreign key (organization_id,project_id) references public.projects(organization_id,id) on delete cascade,
  foreign key (organization_id,client_party_id) references public.business_parties(organization_id,id)
);
create index if not exists ix_revenue_project_date on public.revenue_entries(project_id,issued_at desc);

create table if not exists public.cash_movements (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid,
  direction text not null check (direction in ('in','out')),
  amount_eur numeric(14,2) not null check (amount_eur > 0),
  booked_at timestamptz not null default now(),
  payment_method text,
  reference text,
  related_cost_id uuid references public.cost_entries(id),
  related_revenue_id uuid references public.revenue_entries(id),
  created_by uuid references auth.users(id),
  foreign key (organization_id,project_id) references public.projects(organization_id,id) on delete cascade,
  check (num_nonnulls(related_cost_id,related_revenue_id) <= 1)
);
create index if not exists ix_cash_project_time on public.cash_movements(project_id,booked_at desc);

-- ---------- NOTIFICATIONS / INTEGRATION HEALTH ----------
create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  project_id uuid,
  recipient_user_id uuid references auth.users(id),
  channel text not null check (channel in ('in_app','sms','viber_link','email','push')),
  template_key text not null,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'queued' check (status in ('queued','sent','delivered','failed','read','cancelled')),
  provider_message_id text,
  created_at timestamptz not null default now(),
  sent_at timestamptz,
  foreign key (organization_id,project_id) references public.projects(organization_id,id) on delete cascade
);

create table if not exists public.integration_health (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  integration_name text not null,
  status text not null check (status in ('healthy','degraded','down','unknown')),
  checked_at timestamptz not null default now(),
  latency_ms integer,
  details jsonb not null default '{}'::jsonb
);

-- ---------- SECURITY HELPERS / ROW LEVEL SECURITY ----------
create or replace function app_private.is_org_member(p_org uuid)
returns boolean language sql stable security definer set search_path = public, pg_temp as $$
  select exists (
    select 1 from public.organization_memberships m
    where m.organization_id = p_org and m.user_id = auth.uid() and m.status = 'active'
  );
$$;

create or replace function app_private.has_org_role(p_org uuid, p_roles text[])
returns boolean language sql stable security definer set search_path = public, pg_temp as $$
  select exists (
    select 1 from public.organization_memberships m
    where m.organization_id = p_org and m.user_id = auth.uid()
      and m.status = 'active' and m.role = any(p_roles)
  );
$$;

-- RLS is enabled on all tenant-owned tables. Policies are intentionally conservative.
do $$
declare t text;
begin
  foreach t in array array[
    'organizations','organization_memberships','invitations','business_parties','projects','site_zones',
    'assets','project_assignments','shifts','gps_points','trips','load_tickets','quantity_measurements',
    'operational_events','audit_log','cameras','media_objects','cost_entries','revenue_entries',
    'cash_movements','notifications','integration_health'
  ] loop
    execute format('alter table public.%I enable row level security', t);
  end loop;
end $$;

-- Read access for active members; writes are restricted to operational roles.
create policy org_read on public.organizations for select using (app_private.is_org_member(id));
create policy membership_read on public.organization_memberships for select using (app_private.is_org_member(organization_id));
create policy party_read on public.business_parties for select using (app_private.is_org_member(organization_id));
create policy party_write on public.business_parties for all using (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','finance'])) with check (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','finance']));
create policy projects_read on public.projects for select using (app_private.is_org_member(organization_id));
create policy projects_write on public.projects for all using (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager'])) with check (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager']));
create policy zones_all on public.site_zones for all using (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager'])) with check (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager']));
create policy assets_read on public.assets for select using (app_private.is_org_member(organization_id));
create policy assets_write on public.assets for all using (app_private.has_org_role(organization_id,array['owner','admin','dispatcher'])) with check (app_private.has_org_role(organization_id,array['owner','admin','dispatcher']));
create policy assignments_read on public.project_assignments for select using (app_private.is_org_member(organization_id));
create policy assignments_write on public.project_assignments for all using (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager'])) with check (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager']));
create policy shifts_read on public.shifts for select using (app_private.is_org_member(organization_id));
create policy shifts_insert on public.shifts for insert with check (app_private.is_org_member(organization_id) and (user_id = auth.uid() or app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager'])));
create policy shifts_update on public.shifts for update using (user_id = auth.uid() or app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager'])) with check (user_id = auth.uid() or app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager']));
create policy gps_read on public.gps_points for select using (app_private.is_org_member(organization_id));
create policy gps_insert on public.gps_points for insert with check (app_private.is_org_member(organization_id) and (user_id = auth.uid() or app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager'])));
create policy trips_read on public.trips for select using (app_private.is_org_member(organization_id));
create policy trips_write on public.trips for all using (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager','operator','driver'])) with check (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager','operator','driver']));
create policy loads_read on public.load_tickets for select using (app_private.is_org_member(organization_id));
create policy loads_write on public.load_tickets for all using (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager','operator'])) with check (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager','operator']));
create policy quantities_read on public.quantity_measurements for select using (app_private.is_org_member(organization_id));
create policy quantities_write on public.quantity_measurements for all using (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager','operator','finance'])) with check (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager','operator','finance']));
create policy events_read on public.operational_events for select using (app_private.is_org_member(organization_id));
create policy events_insert on public.operational_events for insert with check (app_private.is_org_member(organization_id));
create policy audit_read on public.audit_log for select using (app_private.has_org_role(organization_id,array['owner','admin','auditor']));
create policy cameras_read on public.cameras for select using (app_private.is_org_member(organization_id));
create policy cameras_write on public.cameras for all using (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager'])) with check (app_private.has_org_role(organization_id,array['owner','admin','dispatcher','site_manager']));
create policy media_read on public.media_objects for select using (app_private.is_org_member(organization_id));
create policy media_insert on public.media_objects for insert with check (app_private.is_org_member(organization_id));
create policy costs_read on public.cost_entries for select using (app_private.has_org_role(organization_id,array['owner','admin','finance','auditor']));
create policy costs_write on public.cost_entries for all using (app_private.has_org_role(organization_id,array['owner','admin','finance'])) with check (app_private.has_org_role(organization_id,array['owner','admin','finance']));
create policy revenue_read on public.revenue_entries for select using (app_private.has_org_role(organization_id,array['owner','admin','finance','auditor']));
create policy revenue_write on public.revenue_entries for all using (app_private.has_org_role(organization_id,array['owner','admin','finance'])) with check (app_private.has_org_role(organization_id,array['owner','admin','finance']));
create policy cash_read on public.cash_movements for select using (app_private.has_org_role(organization_id,array['owner','admin','finance','auditor']));
create policy cash_write on public.cash_movements for all using (app_private.has_org_role(organization_id,array['owner','admin','finance'])) with check (app_private.has_org_role(organization_id,array['owner','admin','finance']));
create policy notifications_read on public.notifications for select using (recipient_user_id = auth.uid() or app_private.has_org_role(organization_id,array['owner','admin','dispatcher']));
create policy integration_read on public.integration_health for select using (app_private.has_org_role(organization_id,array['owner','admin']));

-- Never expose service-role keys in the browser. Storage bucket policies must mirror project membership.
-- Operational event/audit immutability should be enforced further with DB triggers and restricted DB roles
-- before production; do not grant client roles UPDATE/DELETE on event/audit tables.

commit;
