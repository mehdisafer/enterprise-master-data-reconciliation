
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select golden_id
from "mdm_demo"."public"."identity_groups"
where golden_id is null



  
  
      
    ) dbt_internal_test