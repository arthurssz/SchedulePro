-- SchedulePro: reagendamento auditado (aplicado no projeto Supabase em 16/11/2026).
-- SQL versionado para recuperação/novos ambientes; depende do esquema SchedulePro anterior.
begin;
create table if not exists public.appointment_reschedule_history (
 id uuid primary key default gen_random_uuid(),
 establishment_id uuid not null references public.establishments(id),
 appointment_id uuid not null references public.appointments(id),
 old_local_date date not null,
 old_local_time time without time zone not null,
 new_local_date date not null,
 new_local_time time without time zone not null,
 old_starts_at timestamptz not null,
 old_ends_at timestamptz not null,
 new_starts_at timestamptz not null,
 new_ends_at timestamptz not null,
 old_status text not null,
 changed_by uuid not null,
 changed_at timestamptz not null default now()
);
create index if not exists appointment_reschedule_history_appointment_idx
 on public.appointment_reschedule_history(appointment_id, changed_at desc);
alter table public.appointment_reschedule_history enable row level security;
revoke all on public.appointment_reschedule_history from public,anon,authenticated;
grant select on public.appointment_reschedule_history to authenticated;
drop policy if exists "Owner can view own reschedule history" on public.appointment_reschedule_history;
create policy "Owner can view own reschedule history"
 on public.appointment_reschedule_history for select to authenticated
 using (
   exists (
     select 1 from public.establishments e
     where e.id=establishment_id and e.owner_id=(select auth.uid())
   )
 );
CREATE OR REPLACE FUNCTION public.schedulepro_reschedule_internal_appointment(p_establishment_id uuid, p_appointment_id uuid, p_new_local_date date, p_new_local_time time without time zone)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
   v_old public.appointments%rowtype;
   v_est public.establishments%rowtype;
   v_service public.services%rowtype;
   v_prof public.professionals%rowtype;
   v_start timestamptz;
   v_end timestamptz;
   v_end_local timestamp without time zone;
   v_weekday smallint;
begin
   if (select auth.uid()) is null then
       raise exception 'É necessário entrar com Google.';
   end if;

   select * into v_est from public.establishments
   where id=p_establishment_id and owner_id=(select auth.uid())
   and onboarding_completed=true;
   if not found then
       raise exception 'Estabelecimento não ativo ou sem permissão.';
   end if;

   if p_new_local_date is null or p_new_local_time is null
      or p_new_local_time <> date_trunc('minute',p_new_local_time)::time then
       raise exception 'Data ou horário inválido.';
   end if;

   select * into v_old from public.appointments
     where id=p_appointment_id and establishment_id=p_establishment_id
     for update;
   if not found then
       raise exception 'Agendamento não encontrado.';
   end if;
   if v_old.status not in ('scheduled','confirmed') then
       raise exception 'Este agendamento já foi finalizado e não pode ser alterado.';
   end if;
   if v_old.starts_at <= now() then
       raise exception 'Não é possível reagendar um atendimento que já começou.';
   end if;
   if v_old.local_date=p_new_local_date and v_old.local_time=p_new_local_time then
       raise exception 'Escolha uma data ou horário diferente do atual.';
   end if;

   if not exists(
       select 1 from public.customers c
       where c.id=v_old.customer_id and c.establishment_id=p_establishment_id
       and not c.is_archived
   ) then
       raise exception 'Selecione um cliente ativo do seu estabelecimento.';
   end if;

   select * into v_service from public.services
     where id=v_old.service_id and establishment_id=p_establishment_id and is_active=true;
   if not found then
       raise exception 'Serviço indisponível.';
   end if;
   select * into v_prof from public.professionals
     where id=v_old.professional_id and establishment_id=p_establishment_id and is_active=true;
   if not found then
       raise exception 'Profissional indisponível.';
   end if;
   if not exists(
       select 1 from public.professional_services ps
       where ps.establishment_id=p_establishment_id
       and ps.professional_id=v_old.professional_id
       and ps.service_id=v_old.service_id
   ) then
       raise exception 'Profissional não realiza o serviço selecionado.';
   end if;

   v_start := (p_new_local_date+p_new_local_time) at time zone v_est.timezone;
   v_end := v_start + (v_service.duration_minutes * interval '1 minute');
   v_end_local := v_end at time zone v_est.timezone;

   if v_start<=now() then
       raise exception 'Escolha um horário futuro.';
   end if;
   if v_start>now()+interval '365 days' then
       raise exception 'Agendamentos são aceitos até 365 dias à frente.';
   end if;
   if v_end_local::date<>p_new_local_date then
       raise exception 'O serviço precisa terminar no mesmo dia.';
   end if;
   v_weekday := (extract(isodow from p_new_local_date)::integer-1)::smallint;

   if not exists(
       select 1 from public.establishment_weekly_hours eh,
         lateral jsonb_array_elements(eh.intervals) horario
       where eh.establishment_id=p_establishment_id
       and eh.weekday=v_weekday
       and (horario->>'start')::time<=p_new_local_time
       and (horario->>'end')::time>=v_end_local::time
   ) then
       raise exception 'Horário fora do funcionamento do estabelecimento.';
   end if;
   if not exists(
       select 1 from public.professional_weekly_hours ph,
          lateral jsonb_array_elements(ph.intervals) horario
       where ph.establishment_id=p_establishment_id
       and ph.professional_id=v_old.professional_id
       and ph.weekday=v_weekday
       and (horario->>'start')::time<=p_new_local_time
       and (horario->>'end')::time>=v_end_local::time
   ) then
       raise exception 'Horário fora da jornada do profissional.';
   end if;

   perform pg_catalog.pg_advisory_xact_lock(
     pg_catalog.hashtextextended(v_old.professional_id::text,0)
   );
   if exists(
      select 1 from public.appointments a
      where a.professional_id=v_old.professional_id
      and a.id<>p_appointment_id
      and a.status in ('scheduled','confirmed')
      and a.starts_at<v_end and a.ends_at>v_start
   ) then
      raise exception 'Este profissional já tem agendamento nesse horário.';
   end if;

   insert into public.appointment_reschedule_history(
       establishment_id,appointment_id,
       old_local_date,old_local_time,new_local_date,new_local_time,
       old_starts_at,old_ends_at,new_starts_at,new_ends_at,old_status,changed_by
   ) values (
       p_establishment_id,p_appointment_id,
       v_old.local_date,v_old.local_time,p_new_local_date,p_new_local_time,
       v_old.starts_at,v_old.ends_at,v_start,v_end,v_old.status,(select auth.uid())
   );

   update public.appointments
   set local_date=p_new_local_date,
       local_time=p_new_local_time,
       starts_at=v_start,
       ends_at=v_end,
       status='scheduled',
       updated_at=now()
   where id=p_appointment_id and establishment_id=p_establishment_id;

   return jsonb_build_object(
       'id',p_appointment_id,
       'local_date',p_new_local_date,
       'local_time',p_new_local_time,
       'status','scheduled'
   );
end
$function$
;
revoke all on function public.schedulepro_reschedule_internal_appointment(uuid,uuid,date,time without time zone)
 from public,anon,authenticated;
grant execute on function public.schedulepro_reschedule_internal_appointment(uuid,uuid,date,time without time zone)
 to authenticated;
commit;
