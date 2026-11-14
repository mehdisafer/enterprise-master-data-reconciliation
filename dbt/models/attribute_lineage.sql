{% if target.type == 'postgres' %}
select
    g.golden_id,
    g.group_version,
    a.key as attribute_name,
    a.value as attribute_value,
    g.provenance -> a.key as lineage
from {{ ref('golden_records') }} g
cross join lateral jsonb_each(g.attributes) a
{% else %}
select
    g.golden_id,
    g.group_version,
    a.key::varchar as attribute_name,
    a.value as attribute_value,
    get(g.provenance, a.key::varchar) as lineage
from {{ ref('golden_records') }} g,
lateral flatten(input => g.attributes) a
{% endif %}
