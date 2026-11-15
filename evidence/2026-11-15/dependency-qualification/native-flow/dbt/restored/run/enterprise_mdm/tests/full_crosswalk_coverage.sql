
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select s.source_key
from "mdm_restore"."public"."source_records" s
left join "mdm_restore"."analytics"."crosswalk" c on s.source_key = c.source_key
where c.source_key is null
  
  
      
    ) dbt_internal_test