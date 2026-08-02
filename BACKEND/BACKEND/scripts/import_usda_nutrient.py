# scripts/import_usda_nutrient.py
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

def import_nutrients(csv_path):
    conn = None
    cur = None
    inserted = 0
    skipped = 0
    errors = []

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Detect delimiter
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            first_line = f.readline()
            delimiter = ';' if ';' in first_line else ','
            f.seek(0)
            reader = csv.DictReader(f, delimiter=delimiter)
            logger.info(f"Delimiter: '{delimiter}'")

            for row_num, row in enumerate(reader, start=1):
                try:
                    cur.execute("SAVEPOINT row_savepoint")

                    nutrient_id = row.get('id')
                    if not nutrient_id:
                        errors.append(f"Row {row_num}: missing id")
                        cur.execute("ROLLBACK TO SAVEPOINT row_savepoint")
                        continue

                    # Check duplicate
                    cur.execute("SELECT 1 FROM raw_data.usda_nutrient WHERE id = %s", (nutrient_id,))
                    if cur.fetchone():
                        skipped += 1
                        cur.execute("ROLLBACK TO SAVEPOINT row_savepoint")
                        continue

                    # Insert
                    cur.execute("""
                        INSERT INTO raw_data.usda_nutrient
                        (id, name, unit_name, nutrient_nbr, rank, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    """, (
                        nutrient_id,
                        row.get('name'),
                        row.get('unit_name'),
                        row.get('nutrient_nbr'),
                        row.get('rank'),
                    ))
                    inserted += 1
                    cur.execute("RELEASE SAVEPOINT row_savepoint")

                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    logger.warning(f"Row {row_num} failed: {e}")
                    cur.execute("ROLLBACK TO SAVEPOINT row_savepoint")

                if inserted % 1000 == 0:
                    conn.commit()
                    logger.info(f"Inserted {inserted} nutrients")

            conn.commit()
            logger.info(f"Done: {inserted} inserted, {skipped} skipped, {len(errors)} errors")

            # Print first 10 errors
            if errors:
                logger.info("First 10 errors:")
                for i, err in enumerate(errors[:10]):
                    logger.info(f"  {i+1}. {err}")

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python import_usda_nutrient.py <path_to_nutrient.csv>")
        sys.exit(1)
    import_nutrients(sys.argv[1])