select m.source_key, m.golden_id
from "mdm_demo"."public"."memberships" m
join "mdm_demo"."public"."identity_groups" g on m.golden_id = g.golden_id
where g.status <> 'active'