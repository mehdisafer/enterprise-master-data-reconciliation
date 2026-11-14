select
    m.source_key,
    s.source_system,
    s.entity_type,
    s.source_id,
    m.golden_id,
    g.version as group_version
from {{ source('mdm', 'memberships') }} m
join {{ source('mdm', 'source_records') }} s on s.source_key = m.source_key
join {{ source('mdm', 'identity_groups') }} g on g.golden_id = m.golden_id
where g.status = 'active'
