
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select child.source_key, parent.source_key as parent_source_key
from "mdm_restore"."public"."source_records" s
join "mdm_restore"."public"."memberships" child on s.source_key = child.source_key
join "mdm_restore"."public"."memberships" parent
  on (s.current_payload ->> 'parent_source_key') = parent.source_key
where child.golden_id = parent.golden_id
  
  
      
    ) dbt_internal_test