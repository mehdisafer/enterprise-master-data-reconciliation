
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select metric
from "mdm_demo"."analytics"."quality_report"
where metric is null



  
  
      
    ) dbt_internal_test