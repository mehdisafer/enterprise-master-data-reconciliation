
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select source_key
from "mdm_demo"."public"."source_records"
where source_key is null



  
  
      
    ) dbt_internal_test