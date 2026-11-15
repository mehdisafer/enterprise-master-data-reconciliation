with registrations as (
    select m.golden_id,
      (s.current_payload ->> 'country') as country,
      
      upper(regexp_replace((s.current_payload ->> 'registration_id'), '[^A-Za-z0-9]', '', 'g')) as registration_id
      
    from "mdm_demo"."public"."memberships" m
    join "mdm_demo"."public"."source_records" s on s.source_key = m.source_key
    where s.entity_type = 'organization'
)
select golden_id
from registrations
where registration_id is not null and registration_id <> ''
group by golden_id
having count(distinct registration_id) > 1 or count(distinct country) > 1