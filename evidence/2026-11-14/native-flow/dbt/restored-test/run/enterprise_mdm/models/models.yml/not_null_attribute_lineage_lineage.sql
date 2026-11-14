
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select lineage
from "mdm_restore"."analytics"."attribute_lineage"
where lineage is null



  
  
      
    ) dbt_internal_test