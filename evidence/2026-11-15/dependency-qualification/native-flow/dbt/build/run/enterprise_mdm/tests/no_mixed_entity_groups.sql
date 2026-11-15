
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select golden_id
from "mdm_demo"."analytics"."crosswalk"
group by golden_id
having count(distinct entity_type) > 1
  
  
      
    ) dbt_internal_test