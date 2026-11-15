select consumer, event_id
from "mdm_restore"."public"."consumer_inbox"
group by consumer, event_id
having count(*) > 1