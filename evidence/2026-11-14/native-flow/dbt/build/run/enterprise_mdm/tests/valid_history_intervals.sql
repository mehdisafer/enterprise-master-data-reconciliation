
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  select history_id
from "mdm"."public"."golden_history"
where (valid_to is not null and valid_to <= valid_from)
   or (known_to is not null and known_to <= known_from)
   or valid_from is null or known_from is null
  
  
      
    ) dbt_internal_test