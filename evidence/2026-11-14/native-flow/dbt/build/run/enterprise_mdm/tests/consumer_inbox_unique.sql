
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select consumer, event_id
from "mdm"."public"."consumer_inbox"
group by consumer, event_id
having count(*) > 1
  
  
      
    ) dbt_internal_test