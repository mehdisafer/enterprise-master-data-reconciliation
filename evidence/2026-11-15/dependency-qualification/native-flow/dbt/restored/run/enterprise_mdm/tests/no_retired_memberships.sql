
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select m.source_key, m.golden_id
from "mdm_restore"."public"."memberships" m
join "mdm_restore"."public"."identity_groups" g on m.golden_id = g.golden_id
where g.status <> 'active'
  
  
      
    ) dbt_internal_test