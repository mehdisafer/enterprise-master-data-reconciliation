
    
    

select
    golden_id as unique_field,
    count(*) as n_records

from "mdm_restore"."public"."identity_groups"
where golden_id is not null
group by golden_id
having count(*) > 1


