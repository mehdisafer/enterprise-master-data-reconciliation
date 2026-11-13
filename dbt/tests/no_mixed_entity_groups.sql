select golden_id
from {{ ref('crosswalk') }}
group by golden_id
having count(distinct entity_type) > 1
