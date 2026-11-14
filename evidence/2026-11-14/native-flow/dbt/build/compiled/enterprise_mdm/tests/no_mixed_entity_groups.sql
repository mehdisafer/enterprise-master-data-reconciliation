select golden_id
from "mdm"."analytics"."crosswalk"
group by golden_id
having count(distinct entity_type) > 1