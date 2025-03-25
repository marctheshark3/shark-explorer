import asyncio
import psycopg2

async def main():
    # Connect to the database
    conn = psycopg2.connect(
        host="localhost",
        port=5433,
        database="ergo_explorer",
        user="postgres",
        password="postgres"
    )
    
    # Create a cursor
    cur = conn.cursor()
    
    # Execute the query
    cur.execute("SELECT COUNT(*) FROM transactions")
    
    # Fetch the result
    count = cur.fetchone()[0]
    
    print(f"Total transactions in database: {count}")
    
    # Close the connection
    cur.close()
    conn.close()

if __name__ == "__main__":
    asyncio.run(main()) 