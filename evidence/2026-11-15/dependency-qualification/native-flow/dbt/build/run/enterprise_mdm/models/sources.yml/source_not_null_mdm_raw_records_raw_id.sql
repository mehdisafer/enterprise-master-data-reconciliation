
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select raw_id
from "mdm_demo"."public"."raw_records"
where raw_id is null



  
  
      
    ) dbt_internal_test