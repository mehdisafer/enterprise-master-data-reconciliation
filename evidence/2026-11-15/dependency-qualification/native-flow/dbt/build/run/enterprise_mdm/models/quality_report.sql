
  create view "mdm_demo"."analytics"."quality_report__dbt_tmp"
    
    
  as (
    select 'source_records' as metric, count(*) as value from "mdm_demo"."public"."source_records"
union all
select 'golden_records', count(*) from "mdm_demo"."analytics"."golden_records"
union all
select 'suspected_duplicate_pairs', count(*) from "mdm_demo"."public"."candidates"
where disposition in ('auto', 'review', 'group_conflict')
union all
select 'crosswalk_records', count(*) from "mdm_demo"."analytics"."crosswalk"
union all
select 'unmapped_source_records', count(*)
from "mdm_demo"."public"."source_records" s
left join "mdm_demo"."analytics"."crosswalk" c on s.source_key = c.source_key
where c.source_key is null
union all
select 'pending_human_decisions', count(*) from "mdm_demo"."public"."decisions"
where status in ('pending', 'approved')
union all
select 'correction_decisions', count(*) from "mdm_demo"."public"."decisions"
where kind in ('split', 'unmerge') and status = 'executed'
union all
select 'executed_decisions', count(*) from "mdm_demo"."public"."decisions" where status = 'executed'
union all
select 'attributes_without_lineage', count(*) from "mdm_demo"."analytics"."attribute_lineage" where lineage is null
union all
select 'consumer_corrections_pending', count(*) from "mdm_demo"."analytics"."consumer_impact"
where reconciliation_status <> 'aligned'
  );