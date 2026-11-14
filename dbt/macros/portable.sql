{% macro json_text(column, field) -%}
  {%- if target.type == 'postgres' -%}
    ({{ column }} ->> '{{ field }}')
  {%- elif target.type == 'snowflake' -%}
    ({{ column }}:"{{ field }}"::varchar)
  {%- else -%}
    {{ exceptions.raise_compiler_error('Only PostgreSQL and Snowflake are supported') }}
  {%- endif -%}
{%- endmacro %}

{% macro infinity_timestamp() -%}
  cast('9999-12-31 00:00:00+00:00' as {{ dbt.type_timestamp() }})
{%- endmacro %}

{% macro safe_source_schema() -%}
  {%- set value = env_var('MDM_SOURCE_SCHEMA', 'MDM_RAW' if target.type == 'snowflake' else 'public') -%}
  {%- if not modules.re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,62}', value) -%}
    {{ exceptions.raise_compiler_error('MDM_SOURCE_SCHEMA must be a simple SQL identifier') }}
  {%- endif -%}
  {{ return(value) }}
{%- endmacro %}

{% macro validate_mdm_config() -%}
  {%- set names = [safe_source_schema(), target.schema, target.database] -%}
  {%- for name in names -%}
    {%- if not modules.re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,62}', name) -%}
      {{ exceptions.raise_compiler_error('Database and schema names must be simple SQL identifiers') }}
    {%- endif -%}
  {%- endfor -%}
  select 1 as validated_mdm_identifiers
{%- endmacro %}

{% macro snowflake_session_bounds() -%}
  {%- if target.type == 'snowflake' -%}
    alter session set statement_timeout_in_seconds = 120,
      statement_queued_timeout_in_seconds = 30, timezone = 'UTC'
  {%- else -%}
    select 1 as postgres_session_bounds_are_set_by_connection
  {%- endif -%}
{%- endmacro %}
