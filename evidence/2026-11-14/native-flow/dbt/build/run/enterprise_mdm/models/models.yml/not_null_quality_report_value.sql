
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select value
from "mdm"."analytics"."quality_report"
where value is null



  
  
      
    ) dbt_internal_test