
    
    

with all_values as (

    select
        status as value_field,
        count(*) as n_records

    from "mdm"."public"."identity_groups"
    group by status

)

select *
from all_values
where value_field not in (
    'active','retired'
)


