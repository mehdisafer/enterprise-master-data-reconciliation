
    
    

with child as (
    select golden_id as from_field
    from "mdm"."public"."golden_history"
    where golden_id is not null
),

parent as (
    select golden_id as to_field
    from "mdm"."public"."identity_groups"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


