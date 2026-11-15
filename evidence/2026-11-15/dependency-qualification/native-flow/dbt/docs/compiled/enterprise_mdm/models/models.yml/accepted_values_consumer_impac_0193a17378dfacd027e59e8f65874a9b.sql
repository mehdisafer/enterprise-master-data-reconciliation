
    
    

with all_values as (

    select
        reconciliation_status as value_field,
        count(*) as n_records

    from "mdm_demo"."analytics"."consumer_impact"
    group by reconciliation_status

)

select *
from all_values
where value_field not in (
    'aligned','unknown_identity','retirement_pending','activation_pending','update_pending','consumer_ahead'
)


