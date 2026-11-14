
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select provenance
from "mdm"."analytics"."golden_records"
where provenance is null



  
  
      
    ) dbt_internal_test