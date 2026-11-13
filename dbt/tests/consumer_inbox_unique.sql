select consumer, event_id
from {{ source('mdm', 'consumer_inbox') }}
group by consumer, event_id
having count(*) > 1
