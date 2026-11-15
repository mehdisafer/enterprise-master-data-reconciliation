select child.source_key, parent.source_key as parent_source_key
from "mdm_demo"."public"."source_records" s
join "mdm_demo"."public"."memberships" child on s.source_key = child.source_key
join "mdm_demo"."public"."memberships" parent
  on (s.current_payload ->> 'parent_source_key') = parent.source_key
where child.golden_id = parent.golden_id