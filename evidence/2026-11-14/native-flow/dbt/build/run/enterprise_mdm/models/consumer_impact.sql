
  create view "mdm"."analytics"."consumer_impact__dbt_tmp"
    
    
  as (
    select
    c.consumer,
    c.golden_id,
    c.group_version as consumed_version,
    c.active as consumer_active,
    g.version as authoritative_version,
    g.status as authoritative_status,
    case
      when g.golden_id is null then 'unknown_identity'
      when c.active and g.status = 'retired' then 'retirement_pending'
      when not c.active and g.status = 'active' then 'activation_pending'
      when c.group_version < g.version then 'update_pending'
      when c.group_version > g.version then 'consumer_ahead'
      else 'aligned'
    end as reconciliation_status
from "mdm"."public"."consumer_records" c
left join "mdm"."public"."identity_groups" g on c.golden_id = g.golden_id
  );