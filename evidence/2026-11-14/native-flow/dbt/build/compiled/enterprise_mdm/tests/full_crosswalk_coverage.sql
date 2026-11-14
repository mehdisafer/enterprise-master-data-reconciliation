select s.source_key
from "mdm"."public"."source_records" s
left join "mdm"."analytics"."crosswalk" c on s.source_key = c.source_key
where c.source_key is null