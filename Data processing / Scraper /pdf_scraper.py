import asyncio
import aiohttp
import fitz  # PyMuPDF
import io
import os
from crawl4ai import AsyncUrlSeeder, SeedingConfig



async def send_to_storage(session, url, content, title="", metadata=None):

    payload = {
        "url": url,
        "content": content,
        "title": title,
        "metadata": metadata or {}
    }

    async with session.post( "http://127.0.0.1:8000/store", json=payload) as resp:

        if resp.status in (200, 201):
            return await resp.json()
        
        else:
            error_text = await resp.text()
            raise Exception(f"Storage error {resp.status}: {error_text}")

def is_allowed(url):

    try:
        domain = url.split('/')[2].lower()

    except IndexError:
        return False
    
    if 'iiti.ac.in' not in domain:
        return False
    
    blocked = ['mail.iiti.ac.in', 'lms.iiti.ac.in', 'library.iiti.ac.in', 'chemcon.iiti.ac.in']
    return all(b not in domain for b in blocked)

async def download_and_extract_text(session, pdf_url):

    try:

        async with session.get(pdf_url) as resp:

            if resp.status != 200:
                print(f"Failed to download {pdf_url}: status {resp.status}")
                return None
            pdf_bytes = await resp.read()
            
    except Exception as e:
        print(f"Error downloading {pdf_url}: {e}")
        return None

    try:

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page_num in range(len(doc)):

            page = doc.load_page(page_num)
            text += page.get_text()

        doc.close()
        return text
    
    except Exception as e:

        print(f"Error extracting text from {pdf_url}: {e}")
        return None

async def main():
    
    async with AsyncUrlSeeder() as seeder:

        discovery_config = SeedingConfig(source="sitemap+cc")
        result_urls = await seeder.urls("https://www.iiti.ac.in/", config=discovery_config)

    filtered_urls = []

    for item in result_urls:

        url = item['url']
        if is_allowed(url):
            filtered_urls.append(url)
        else:
            print(f"Skipping {url} (domain filter)")

    pdf_urls = [url for url in filtered_urls if url.lower().endswith('.pdf')]
    print(f"Found {len(pdf_urls)} PDF URLs")

    async with aiohttp.ClientSession() as session:

        for i, pdf_url in enumerate(pdf_urls, start=1):

            print(f"[{i}/{len(pdf_urls)}] Processing {pdf_url}")

            text = await download_and_extract_text(session, pdf_url)

            if text:
                
                try:
                    response = await send_to_storage(
                        session,
                        url=pdf_url,
                        content=text,
                        title=os.path.basename(pdf_url),  
                        metadata={}
                    )

                    print(f"  Stored: {response['message']}")

                except Exception as e:
                    print(f"  Failed to store: {e}")

            else:
                print(f"  Failed to extract text, skipping")

if __name__ == "__main__":
    asyncio.run(main())
