
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select consumer, golden_id
from "mdm_demo"."public"."consumer_records"
group by consumer, golden_id
having count(*) > 1
  
  
      
    ) dbt_internal_test