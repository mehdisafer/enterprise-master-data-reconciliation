select consumer, event_id
from "mdm_demo"."public"."consumer_inbox"
group by consumer, event_id
having count(*) > 1