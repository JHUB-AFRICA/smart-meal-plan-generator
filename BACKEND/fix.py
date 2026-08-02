import os, re, glob
files = glob.glob('migrations/versions/*_initial_schema.py')
if not files:
    print("Error: No migration file found.")
    exit(1)
f = max(files, key=os.path.getctime)
print(f"Fixing constraint table mapping in: {f}")

with open(f, 'r') as file:
    data = file.read()

constraints_map = {
    'fk_meal_plans_created_by': 'meal_plans',
    'fk_meal_plans_client': 'meal_plans',
    'fk_meal_plans_professional': 'meal_plans',
    'fk_professionals_subscription_plan': 'professionals',
    'fk_reports_client': 'reports'
}

def fix_constraint(m):
    c = m.group(1)
    parts = c.split('_')
    if c.startswith('fk_'):
        table = constraints_map.get(c, parts[1] if len(parts) > 1 else 'unknown')
    else:
        # CORRECTED: Correctly removes the column name (e.g., user_id) and the suffix '_fkey'
        table = '_'.join(parts[:-3]) if len(parts) > 3 else 'unknown'
    return f"op.execute('ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {c};')"

data = re.sub(r"batch_op\.drop_constraint\(batch_op\.f\('([^']+)'\), type_='[^']+'\)", fix_constraint, data)

with open(f, 'w') as file:
    file.write(data)
print("Migration constraints fixed successfully!")
