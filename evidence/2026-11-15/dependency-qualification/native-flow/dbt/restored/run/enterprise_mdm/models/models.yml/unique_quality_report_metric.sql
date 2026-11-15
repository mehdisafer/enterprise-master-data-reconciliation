
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    metric as unique_field,
    count(*) as n_records

from "mdm_restore"."analytics"."quality_report"
where metric is not null
group by metric
having count(*) > 1



  
  
      
    ) dbt_internal_test