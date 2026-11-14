select consumer, golden_id
from "mdm_restore"."public"."consumer_records"
group by consumer, golden_id
having count(*) > 1