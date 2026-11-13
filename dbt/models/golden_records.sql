select
    h.golden_id,
    g.entity_type,
    h.group_version,
    h.attributes,
    h.provenance,
    h.conflicts,
    h.valid_from,
    h.valid_to,
    h.known_from,
    {{ json_text('h.attributes', 'name') }} as display_name,
    {{ json_text('h.attributes', 'registration_id') }} as registration_id
from {{ source('mdm', 'golden_history') }} h
join {{ source('mdm', 'identity_groups') }} g on h.golden_id = g.golden_id
where g.status = 'active'
  and h.known_to is null
  and h.valid_from <= current_timestamp
  and (h.valid_to is null or h.valid_to > current_timestamp)
