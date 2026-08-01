# scripts/import_usda_staging.py
import os
import sys
import csv
import psycopg2
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URI = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/smartlishe_db')

def get_connection():
    return psycopg2.connect(DB_URI)

def main(csv_path, final_table, target_columns):
    conn = get_connection()
    cur = conn.cursor()

    # 1. Detect delimiter and read header
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        first_line = f.readline()
        delimiter = ';' if ';' in first_line else ','
        f.seek(0)
        reader = csv.DictReader(f, delimiter=delimiter)
        header = reader.fieldnames
        logger.info(f"Delimiter: '{delimiter}'")
        logger.info(f"CSV header: {header}")

    # 2. Create a staging table with all columns as TEXT
    staging_table = f"staging_{final_table}"
    create_sql = "CREATE TABLE raw_data.{} (".format(staging_table)
    create_sql += ', '.join([f'"{col}" TEXT' for col in header])
    create_sql += ");"
    cur.execute(create_sql)
    conn.commit()
    logger.info(f"Staging table raw_data.{staging_table} created")

    # 3. Import CSV into staging table using COPY
    col_list = ', '.join([f'"{col}"' for col in header])
    copy_sql = f"COPY raw_data.{staging_table} ({col_list}) FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER '{delimiter}', ENCODING 'UTF8')"
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        cur.copy_expert(copy_sql, f)
    conn.commit()
    logger.info(f"CSV imported into staging table")

    # 4. Insert only the needed columns into the final table
    select_cols = ', '.join([f'"{col}"' for col in target_columns])
    insert_sql = f"""
        INSERT INTO raw_data.{final_table} ({select_cols}, created_at, updated_at)
        SELECT {select_cols}, NOW(), NOW()
        FROM raw_data.{staging_table}
    """
    cur.execute(insert_sql)
    conn.commit()
    logger.info(f"Data inserted into raw_data.{final_table}")

    # 5. Drop staging table
    cur.execute(f"DROP TABLE raw_data.{staging_table}")
    conn.commit()
    logger.info("Staging table dropped")

    # 6. Count rows
    cur.execute(f"SELECT COUNT(*) FROM raw_data.{final_table}")
    count = cur.fetchone()[0]
    logger.info(f"Total rows in {final_table}: {count}")

    cur.close()
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python import_usda_staging.py <csv_path> <final_table> <col1,col2,...>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3].split(','))