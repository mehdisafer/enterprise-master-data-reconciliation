-- Both validity and knowledge ranges must overlap for two slices to conflict.
select a.history_id, b.history_id as conflicting_history_id
from "mdm_restore"."public"."golden_history" a
join "mdm_restore"."public"."golden_history" b
  on a.golden_id = b.golden_id
 and cast(a.history_id as TEXT) < cast(b.history_id as TEXT)
 and a.valid_from < coalesce(b.valid_to, cast('9999-12-31 00:00:00+00:00' as timestamp))
 and b.valid_from < coalesce(a.valid_to, cast('9999-12-31 00:00:00+00:00' as timestamp))
 and a.known_from < coalesce(b.known_to, cast('9999-12-31 00:00:00+00:00' as timestamp))
 and b.known_from < coalesce(a.known_to, cast('9999-12-31 00:00:00+00:00' as timestamp))