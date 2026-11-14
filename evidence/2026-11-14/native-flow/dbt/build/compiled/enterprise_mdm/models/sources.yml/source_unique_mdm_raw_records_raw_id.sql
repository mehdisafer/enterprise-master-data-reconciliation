
    
    

select
    raw_id as unique_field,
    count(*) as n_records

from "mdm"."public"."raw_records"
where raw_id is not null
group by raw_id
having count(*) > 1


