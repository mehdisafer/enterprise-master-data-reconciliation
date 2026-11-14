
    
    

select
    source_key as unique_field,
    count(*) as n_records

from "mdm"."public"."source_records"
where source_key is not null
group by source_key
having count(*) > 1


