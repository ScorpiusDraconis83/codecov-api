# Generated by Django 3.1.13 on 2022-05-24 14:51

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("timeseries", "0002_continuous_aggregates"),
    ]

    operations = [
        migrations.RunSQL(
            f"""
            select add_continuous_aggregate_policy(
                'timeseries_measurement_summary_{name}',
                start_offset => NULL,
                end_offset => NULL,
                schedule_interval => INTERVAL '24 hours'
            );
            """,
            reverse_sql=f"select remove_continuous_aggregate_policy('timeseries_measurement_summary_{name}');",
        )
        for name in ["1day", "7day", "30day"]
    ]
