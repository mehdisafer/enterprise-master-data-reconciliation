
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  with attributes as (
    
    select h.history_id, a.key as attribute_name, a.value as attribute_value,
           h.provenance -> a.key as lineage
    from "mdm_restore"."public"."golden_history" h
    cross join lateral jsonb_each(h.attributes) a
    where a.value not in ('null'::jsonb, '[]'::jsonb)
    
), lineage as (
    select a.*,
      nullif((a.lineage ->> 'source_key'), 'null') as source_key,
      nullif((a.lineage ->> 'rule'), 'null') as rule_version,
      nullif((a.lineage ->> 'source_updated_at'), 'null') as source_updated_at,
      nullif((a.lineage ->> 'valid_from'), 'null') as valid_from
    from attributes a
)
select a.history_id, a.attribute_name
from lineage a
left join "mdm_restore"."public"."source_records" s on s.source_key = a.source_key
where s.source_key is null or a.rule_version is null
   or a.source_updated_at is null or a.valid_from is null
   or (a.attribute_name <> 'roles' and not exists (
       select 1 from "mdm_restore"."public"."raw_records" r
       where r.source_key = a.source_key
       
         and r.payload -> a.attribute_name = a.attribute_value
       
   ))
  
  
      
    ) dbt_internal_test