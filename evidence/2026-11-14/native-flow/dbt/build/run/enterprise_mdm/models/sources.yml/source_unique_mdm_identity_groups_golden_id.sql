
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    golden_id as unique_field,
    count(*) as n_records

from "mdm"."public"."identity_groups"
where golden_id is not null
group by golden_id
having count(*) > 1



  
  
      
    ) dbt_internal_test