# scripts/import_usda.py
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

def import_csv(table_name, csv_path, columns):
    conn = get_connection()
    cur = conn.cursor()
    inserted = 0
    skipped = 0
    errors = []

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            first_line = f.readline()
            delimiter = ';' if ';' in first_line else ','
            f.seek(0)
            reader = csv.DictReader(f, delimiter=delimiter)
            logger.info(f"Table: {table_name}, delimiter: '{delimiter}', columns: {columns}")

            for row_num, row in enumerate(reader, start=1):
                try:
                    cur.execute("SAVEPOINT row_savepoint")
                    placeholders = ', '.join(['%s'] * len(columns))
                    col_names = ', '.join(columns)
                    sql = f"INSERT INTO raw_data.{table_name} ({col_names}, created_at, updated_at) VALUES ({placeholders}, NOW(), NOW())"
                    values = [row.get(col) for col in columns]
                    cur.execute(sql, values)
                    inserted += 1
                    cur.execute("RELEASE SAVEPOINT row_savepoint")
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    logger.warning(f"Row {row_num} failed: {e}")
                    cur.execute("ROLLBACK TO SAVEPOINT row_savepoint")
                if inserted % 1000 == 0:
                    conn.commit()
                    logger.info(f"Inserted {inserted} rows")
            conn.commit()
            logger.info(f"Done: {inserted} inserted, {skipped} skipped, {len(errors)} errors")
            if errors:
                logger.info("First 5 errors:")
                for i, err in enumerate(errors[:5]):
                    logger.info(f"  {i+1}. {err}")
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python import_usda.py <table_name> <csv_path> <col1,col2,...>")
        sys.exit(1)
    import_csv(sys.argv[1], sys.argv[2], sys.argv[3].split(','))