select m.source_key, m.golden_id
from {{ source('mdm', 'memberships') }} m
join {{ source('mdm', 'identity_groups') }} g on m.golden_id = g.golden_id
where g.status <> 'active'
