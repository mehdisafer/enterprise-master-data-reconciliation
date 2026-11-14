
  create view "mdm"."analytics"."crosswalk__dbt_tmp"
    
    
  as (
    select
    m.source_key,
    s.source_system,
    s.entity_type,
    s.source_id,
    m.golden_id,
    g.version as group_version
from "mdm"."public"."memberships" m
join "mdm"."public"."source_records" s on s.source_key = m.source_key
join "mdm"."public"."identity_groups" g on g.golden_id = m.golden_id
where g.status = 'active'
  );