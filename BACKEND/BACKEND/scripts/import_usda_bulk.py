# scripts/import_usda_bulk.py
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

def bulk_import(table_name, csv_path, columns):
    """
    Bulk import CSV into raw_data.<table_name> using COPY.
    columns: list of column names in order.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Detect delimiter
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        first_line = f.readline()
        delimiter = ';' if ';' in first_line else ','
        logger.info(f"Detected delimiter: '{delimiter}'")

    # Build COPY command
    col_names = ', '.join(columns)
    sql = f"COPY raw_data.{table_name} ({col_names}) FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER '{delimiter}', ENCODING 'UTF8')"

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            # Skip header (COPY with HEADER true handles it, but we need to skip the first line manually for copy_expert)
            # Actually copy_expert with HEADER true will skip the first line automatically.
            cur.copy_expert(sql, f)
        conn.commit()
        logger.info(f"✅ Import completed successfully for {table_name}")

        # Count rows
        cur.execute(f"SELECT COUNT(*) FROM raw_data.{table_name}")
        count = cur.fetchone()[0]
        logger.info(f"Total rows in {table_name}: {count}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Import failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python import_usda_bulk.py <table_name> <csv_path> <col1,col2,...>")
        sys.exit(1)
    table = sys.argv[1]
    path = sys.argv[2]
    cols = sys.argv[3].split(',')
    bulk_import(table, path, cols)