# scripts/merge_usda_fast.py
import os
import sys
import psycopg2
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_URI = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/smartlishe_db')

def get_connection():
    return psycopg2.connect(DB_URI)

# Map USDA nutrient IDs to public.foods columns
NUTRIENT_MAP = {
    '1008': 'calories',
    '1003': 'protein',
    '1004': 'fat',
    '1005': 'carbohydrates',
    '1079': 'fiber',
    '1010': 'sugar',
    '1093': 'sodium',
    '1087': 'calcium',
    '1089': 'iron',
    '1092': 'potassium',
    '1105': 'vitamin_a',
    '1162': 'vitamin_c',
}

def merge():
    conn = get_connection()
    cur = conn.cursor()

    # 1. Insert food categories (skip null names)
    cur.execute("""
        INSERT INTO public.food_categories (id, name, description, created_at, updated_at)
        SELECT DISTINCT
            uuid_generate_v4(),
            fc.name,
            fc.description,
            NOW(),
            NOW()
        FROM raw_data.usda_food_category fc
        WHERE fc.name IS NOT NULL AND fc.name != ''
        AND NOT EXISTS (
            SELECT 1 FROM public.food_categories pc WHERE pc.name = fc.name
        )
    """)
    conn.commit()
    logger.info("Food categories updated")

    # 2. Insert foods (skip duplicates by source + name)
    cur.execute("""
        INSERT INTO public.foods (
            id, name, category_id, serving_size,
            calories, protein, fat, carbohydrates, fiber, sugar,
            sodium, calcium, iron, potassium, vitamin_a, vitamin_c,
            source, source_id, country, image_url, search_keywords,
            is_verified, created_at, updated_at
        )
        SELECT
            uuid_generate_v4(),
            LEFT(f.description, 255),
            pc.id,
            NULL,
            NULL, NULL, NULL, NULL, NULL, NULL,
            NULL, NULL, NULL, NULL, NULL, NULL,
            'USDA',
            f.fdc_id,
            'USA',
            NULL,
            NULL,
            TRUE,
            NOW(),
            NOW()
        FROM raw_data.usda_food f
        LEFT JOIN raw_data.usda_food_category fc ON f.food_category_id = fc.id
        LEFT JOIN public.food_categories pc ON pc.name = fc.name
        WHERE f.description IS NOT NULL AND f.description != ''
        AND NOT EXISTS (
            SELECT 1 FROM public.foods pf
            WHERE pf.name = LEFT(f.description, 255)
            AND pf.source = 'USDA'
        )
    """)
    conn.commit()
    logger.info("Foods inserted")

    # 3. Build a temp table with one row per fdc_id and all nutrient columns
    logger.info("Building nutrient aggregation…")
    cur.execute("""
        DROP TABLE IF EXISTS tmp_nutrients CASCADE;
        CREATE TEMP TABLE tmp_nutrients AS
        SELECT
            fdc_id,
            MAX(CASE WHEN nutrient_id = '1008' THEN amount ELSE NULL END) AS calories,
            MAX(CASE WHEN nutrient_id = '1003' THEN amount ELSE NULL END) AS protein,
            MAX(CASE WHEN nutrient_id = '1004' THEN amount ELSE NULL END) AS fat,
            MAX(CASE WHEN nutrient_id = '1005' THEN amount ELSE NULL END) AS carbohydrates,
            MAX(CASE WHEN nutrient_id = '1079' THEN amount ELSE NULL END) AS fiber,
            MAX(CASE WHEN nutrient_id = '1010' THEN amount ELSE NULL END) AS sugar,
            MAX(CASE WHEN nutrient_id = '1093' THEN amount ELSE NULL END) AS sodium,
            MAX(CASE WHEN nutrient_id = '1087' THEN amount ELSE NULL END) AS calcium,
            MAX(CASE WHEN nutrient_id = '1089' THEN amount ELSE NULL END) AS iron,
            MAX(CASE WHEN nutrient_id = '1092' THEN amount ELSE NULL END) AS potassium,
            MAX(CASE WHEN nutrient_id = '1105' THEN amount ELSE NULL END) AS vitamin_a,
            MAX(CASE WHEN nutrient_id = '1162' THEN amount ELSE NULL END) AS vitamin_c
        FROM raw_data.usda_food_nutrient
        WHERE nutrient_id IN ('1008','1003','1004','1005','1079','1010','1093','1087','1089','1092','1105','1162')
        GROUP BY fdc_id;
    """)
    conn.commit()
    logger.info("Temporary nutrient table created")

    # 4. Update foods in a single query
    logger.info("Updating nutrient values…")
    cur.execute("""
        UPDATE public.foods
        SET
            calories = tn.calories::NUMERIC,
            protein = tn.protein::NUMERIC,
            fat = tn.fat::NUMERIC,
            carbohydrates = tn.carbohydrates::NUMERIC,
            fiber = tn.fiber::NUMERIC,
            sugar = tn.sugar::NUMERIC,
            sodium = tn.sodium::NUMERIC,
            calcium = tn.calcium::NUMERIC,
            iron = tn.iron::NUMERIC,
            potassium = tn.potassium::NUMERIC,
            vitamin_a = tn.vitamin_a::NUMERIC,
            vitamin_c = tn.vitamin_c::NUMERIC
        FROM tmp_nutrients tn
        WHERE public.foods.source_id = tn.fdc_id
          AND public.foods.source = 'USDA';
    """)
    conn.commit()
    logger.info("Nutrients updated")

    # 5. Clean up
    cur.execute("DROP TABLE IF EXISTS tmp_nutrients")
    conn.commit()

    cur.close()
    conn.close()
    logger.info("Merge completed successfully")

if __name__ == '__main__':
    merge()