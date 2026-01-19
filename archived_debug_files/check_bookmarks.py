#!/usr/bin/env python3
"""Verifica quantos bookmarks ainda existem no banco"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Conta total
response = supabase.table('bookmarks').select('id', count='exact').execute()
total = response.count
print(f"📊 Total de bookmarks no banco: {total}")

# Conta por status de processamento
pending = supabase.table('bookmarks').select('id', count='exact').eq('processing_status', 'pending').execute()
queued = supabase.table('bookmarks').select('id', count='exact').eq('processing_status', 'queued').execute()
processing = supabase.table('bookmarks').select('id', count='exact').eq('processing_status', 'processing').execute()
completed = supabase.table('bookmarks').select('id', count='exact').eq('processing_status', 'completed').execute()
failed = supabase.table('bookmarks').select('id', count='exact').eq('processing_status', 'failed').execute()

print(f"\n📋 Por status:")
print(f"   pending: {pending.count}")
print(f"   queued: {queued.count}")
print(f"   processing: {processing.count}")
print(f"   completed: {completed.count}")
print(f"   failed: {failed.count}")
