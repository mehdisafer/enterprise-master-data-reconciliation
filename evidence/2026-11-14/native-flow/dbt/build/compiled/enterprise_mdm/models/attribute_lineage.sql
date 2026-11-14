
select
    g.golden_id,
    g.group_version,
    a.key as attribute_name,
    a.value as attribute_value,
    g.provenance -> a.key as lineage
from "mdm"."analytics"."golden_records" g
cross join lateral jsonb_each(g.attributes) a
