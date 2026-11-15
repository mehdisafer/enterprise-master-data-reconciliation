select golden_id
from "mdm_demo"."analytics"."crosswalk"
group by golden_id
having count(distinct entity_type) > 1