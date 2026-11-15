
  create view "mdm_demo"."analytics"."golden_records__dbt_tmp"
    
    
  as (
    select
    h.golden_id,
    g.entity_type,
    h.group_version,
    h.attributes,
    h.provenance,
    h.conflicts,
    h.valid_from,
    h.valid_to,
    h.known_from,
    (h.attributes ->> 'name') as display_name,
    (h.attributes ->> 'registration_id') as registration_id
from "mdm_demo"."public"."golden_history" h
join "mdm_demo"."public"."identity_groups" g on h.golden_id = g.golden_id
where g.status = 'active'
  and h.known_to is null
  and h.valid_from <= current_timestamp
  and (h.valid_to is null or h.valid_to > current_timestamp)
  );