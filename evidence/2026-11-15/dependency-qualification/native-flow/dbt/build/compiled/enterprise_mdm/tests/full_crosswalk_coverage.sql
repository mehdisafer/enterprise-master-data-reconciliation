select s.source_key
from "mdm_demo"."public"."source_records" s
left join "mdm_demo"."analytics"."crosswalk" c on s.source_key = c.source_key
where c.source_key is null