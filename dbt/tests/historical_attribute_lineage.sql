with attributes as (
    {% if target.type == 'postgres' %}
    select h.history_id, a.key as attribute_name, a.value as attribute_value,
           h.provenance -> a.key as lineage
    from {{ source('mdm', 'golden_history') }} h
    cross join lateral jsonb_each(h.attributes) a
    where a.value not in ('null'::jsonb, '[]'::jsonb)
    {% else %}
    select h.history_id, a.key::varchar as attribute_name, a.value as attribute_value,
           get(h.provenance, a.key::varchar) as lineage
    from {{ source('mdm', 'golden_history') }} h,
    lateral flatten(input => h.attributes) a
    where not is_null_value(a.value)
      and not (is_array(a.value) and array_size(a.value) = 0)
    {% endif %}
), lineage as (
    select a.*,
      nullif({{ json_text('a.lineage', 'source_key') }}, 'null') as source_key,
      nullif({{ json_text('a.lineage', 'rule') }}, 'null') as rule_version,
      nullif({{ json_text('a.lineage', 'source_updated_at') }}, 'null') as source_updated_at,
      nullif({{ json_text('a.lineage', 'valid_from') }}, 'null') as valid_from
    from attributes a
)
select a.history_id, a.attribute_name
from lineage a
left join {{ source('mdm', 'source_records') }} s on s.source_key = a.source_key
where s.source_key is null or a.rule_version is null
   or a.source_updated_at is null or a.valid_from is null
   or (a.attribute_name <> 'roles' and not exists (
       select 1 from {{ source('mdm', 'raw_records') }} r
       where r.source_key = a.source_key
       {% if target.type == 'postgres' %}
         and r.payload -> a.attribute_name = a.attribute_value
       {% else %}
         and get(r.payload, a.attribute_name) = a.attribute_value
       {% endif %}
   ))
