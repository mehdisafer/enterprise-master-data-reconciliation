select
    m.source_key,
    s.source_system,
    s.entity_type,
    s.source_id,
    m.golden_id,
    g.version as group_version
from "mdm_demo"."public"."memberships" m
join "mdm_demo"."public"."source_records" s on s.source_key = m.source_key
join "mdm_demo"."public"."identity_groups" g on g.golden_id = m.golden_id
where g.status = 'active'