select consumer, golden_id
from {{ source('mdm', 'consumer_records') }}
group by consumer, golden_id
having count(*) > 1
