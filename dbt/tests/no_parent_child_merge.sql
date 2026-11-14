select child.source_key, parent.source_key as parent_source_key
from {{ source('mdm', 'source_records') }} s
join {{ source('mdm', 'memberships') }} child on s.source_key = child.source_key
join {{ source('mdm', 'memberships') }} parent
  on {{ json_text('s.current_payload', 'parent_source_key') }} = parent.source_key
where child.golden_id = parent.golden_id
