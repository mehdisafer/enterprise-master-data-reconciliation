-- Both validity and knowledge ranges must overlap for two slices to conflict.
select a.history_id, b.history_id as conflicting_history_id
from {{ source('mdm', 'golden_history') }} a
join {{ source('mdm', 'golden_history') }} b
  on a.golden_id = b.golden_id
 and cast(a.history_id as {{ dbt.type_string() }}) < cast(b.history_id as {{ dbt.type_string() }})
 and a.valid_from < coalesce(b.valid_to, {{ infinity_timestamp() }})
 and b.valid_from < coalesce(a.valid_to, {{ infinity_timestamp() }})
 and a.known_from < coalesce(b.known_to, {{ infinity_timestamp() }})
 and b.known_from < coalesce(a.known_to, {{ infinity_timestamp() }})
