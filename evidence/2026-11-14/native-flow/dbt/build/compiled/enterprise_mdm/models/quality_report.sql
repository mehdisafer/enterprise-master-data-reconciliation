select 'source_records' as metric, count(*) as value from "mdm"."public"."source_records"
union all
select 'golden_records', count(*) from "mdm"."analytics"."golden_records"
union all
select 'suspected_duplicate_pairs', count(*) from "mdm"."public"."candidates"
where disposition in ('auto', 'review', 'group_conflict')
union all
select 'crosswalk_records', count(*) from "mdm"."analytics"."crosswalk"
union all
select 'unmapped_source_records', count(*)
from "mdm"."public"."source_records" s
left join "mdm"."analytics"."crosswalk" c on s.source_key = c.source_key
where c.source_key is null
union all
select 'pending_human_decisions', count(*) from "mdm"."public"."decisions"
where status in ('pending', 'approved')
union all
select 'correction_decisions', count(*) from "mdm"."public"."decisions"
where kind in ('split', 'unmerge') and status = 'executed'
union all
select 'executed_decisions', count(*) from "mdm"."public"."decisions" where status = 'executed'
union all
select 'attributes_without_lineage', count(*) from "mdm"."analytics"."attribute_lineage" where lineage is null
union all
select 'consumer_corrections_pending', count(*) from "mdm"."analytics"."consumer_impact"
where reconciliation_status <> 'aligned'