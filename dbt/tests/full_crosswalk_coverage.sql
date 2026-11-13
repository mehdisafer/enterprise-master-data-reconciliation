select s.source_key
from {{ source('mdm', 'source_records') }} s
left join {{ ref('crosswalk') }} c on s.source_key = c.source_key
where c.source_key is null
