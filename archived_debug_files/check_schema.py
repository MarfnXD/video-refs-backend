from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# Pegar 1 bookmark para ver schema
result = supabase.table('bookmarks').select('*').limit(1).execute()

if result.data:
    print("Campos disponíveis:")
    for key in result.data[0].keys():
        value = result.data[0][key]
        value_type = type(value).__name__
        print(f"  - {key}: {value_type}")
