select 'source_records' as metric, count(*) as value from {{ source('mdm', 'source_records') }}
union all
select 'golden_records', count(*) from {{ ref('golden_records') }}
union all
select 'suspected_duplicate_pairs', count(*) from {{ source('mdm', 'candidates') }}
where disposition in ('auto', 'review', 'group_conflict')
union all
select 'crosswalk_records', count(*) from {{ ref('crosswalk') }}
union all
select 'unmapped_source_records', count(*)
from {{ source('mdm', 'source_records') }} s
left join {{ ref('crosswalk') }} c on s.source_key = c.source_key
where c.source_key is null
union all
select 'pending_human_decisions', count(*) from {{ source('mdm', 'decisions') }}
where status in ('pending', 'approved')
union all
select 'correction_decisions', count(*) from {{ source('mdm', 'decisions') }}
where kind in ('split', 'unmerge') and status = 'executed'
union all
select 'executed_decisions', count(*) from {{ source('mdm', 'decisions') }} where status = 'executed'
union all
select 'attributes_without_lineage', count(*) from {{ ref('attribute_lineage') }} where lineage is null
union all
select 'consumer_corrections_pending', count(*) from {{ ref('consumer_impact') }}
where reconciliation_status <> 'aligned'
