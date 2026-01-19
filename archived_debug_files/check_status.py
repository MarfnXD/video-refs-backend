from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

ids = [
    '7c91f5ca-910b-4eda-b2ad-828c2f5f4e6e',
    'd35673ee-a112-48fe-9bf1-bafa3248d08d',
    '0223b7a0-8f46-4f16-b365-a7bbd5d6929d',
    '4a5d996b-4ac8-432c-b1f7-7beb1d3ee2ac',
    '2a6a9138-a57c-4c32-8a0c-30aa124087a8'
]

for id in ids:
    res = supabase.table('bookmarks').select('smart_title, processing_status, cloud_thumbnail_url, cloud_video_url').eq('id', id).single().execute()
    d = res.data
    print(f"{id[:8]} | {d['processing_status']:12} | thumb:{bool(d['cloud_thumbnail_url'])} | video:{bool(d['cloud_video_url'])} | {(d['smart_title'] or 'Sem título')[:40]}")
