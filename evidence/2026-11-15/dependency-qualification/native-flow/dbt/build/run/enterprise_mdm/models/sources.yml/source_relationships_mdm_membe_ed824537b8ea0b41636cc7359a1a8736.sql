
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with child as (
    select golden_id as from_field
    from "mdm_demo"."public"."memberships"
    where golden_id is not null
),

parent as (
    select golden_id as to_field
    from "mdm_demo"."public"."identity_groups"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



  
  
      
    ) dbt_internal_test