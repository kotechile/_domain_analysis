import asyncio
try:
    import asyncpg
    has_asyncpg = True
except ImportError:
    has_asyncpg = False

async def main():
    if not has_asyncpg:
        print("asyncpg not installed")
        return
        
    try:
        conn = await asyncpg.connect('postgresql://postgres:HP8M73FcyfkNCVLGfA2R74vUSiPDgkhX@localhost:5434/postgres')
        rows = await conn.fetch("SELECT status, error_message, current_stage, total_records, processed_records FROM csv_upload_progress WHERE filename = 'godaddy_today.json' ORDER BY created_at DESC LIMIT 1;")
        if rows:
            print("Error details:")
            print(dict(rows[0]))
        else:
            print("No row found.")
        await conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
