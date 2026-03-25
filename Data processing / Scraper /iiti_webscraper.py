import asyncio
from crawl4ai import AsyncWebCrawler , CrawlerRunConfig , AsyncUrlSeeder , SeedingConfig , CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain,DomainFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import aiohttp

async def send_to_storage(session: aiohttp.ClientSession ,url: str,content : str,title :str = "",metadata: dict= None):
        
    payload = {
        "url" : url,
        "content" :content,
        "title" : title,
        "metadata" : metadata or {}
    }

    async with session.post("http://127.0.0.1:8000/store",json=payload) as resp:
        if resp.status in (200,201):
            return await resp.json()

        else:
            error_text = await resp.text()
            raise Exception(f"Storage error {resp.status}: {error_text}")
    

async def main():


    async with AsyncUrlSeeder() as seeder:

        discovery_config = SeedingConfig(
            source= "sitemap+cc"
        )

        result_urls= await seeder.urls("https://www.iiti.ac.in/",config=discovery_config)

    filter_chain = FilterChain([

        DomainFilter(

            allowed_domains=["iiti.ac.in"],
            blocked_domains=["mail.iiti.ac.in","lms.iiti.ac.in","library.iiti.ac.in","chemcon.iiti.ac.in"] 

        )
    ])

    run_config = CrawlerRunConfig(
        deep_crawl_strategy= BFSDeepCrawlStrategy(
            max_depth=0,
            include_external=False,
            filter_chain=filter_chain,
            max_pages=6000 # -> tweak this according to the site i guess this was done for testing and faster debugging 
        ),
         
        verbose=True,
        stream=False, # stream on is generally recommended but for testing i turned of the stream 
        preserve_https_for_internal_links=True,
        cache_mode=CacheMode.DISABLED,
        markdown_generator=DefaultMarkdownGenerator(
            options={
                "citations": True,
                "body_width": 0
            }
        ),

        excluded_tags=['nav', 'footer', 'header', 'aside', 'script', 'style'],
        word_count_threshold=5,
        page_timeout=120000,
        wait_until="domcontentloaded",
        js_code="""window.scrollTo(0,document.body.scrollHeight);
        await new Promise(resolve => setTimeout(resolve, 5000));
        """
    )

    async with AsyncWebCrawler() as crawler:

        print("Strating the crawl on the discovered urls")

        target_list=[]

        target_list = [item['url'] for item in result_urls]

        results = await crawler.arun_many(target_list, config=run_config) # this code block will change a bit with respect to the chnages in the stream
        
        async with aiohttp.ClientSession() as session:

            count=0
            print("Processing results...")
            for result in results:

                count+=1

                print(f"result.success - {result.success}")
            
                if result.success:
                    print(f"[{count}] Scraped successfully, sending to storage...")
                    # extract title
                    metadata = getattr(result,'metadata', {}) or {}
                    title = metadata.get('title', '') if isinstance(metadata,dict) else ''

                    try:
                        response = await send_to_storage(
                            session,
                            url = result.url,
                            content = result.markdown.raw_markdown,
                            title = title,
                            metadata = {}
                        )

                        print(f"[{count}] Stored : {response['message']} for {result.url}")

                    except Exception as e:

                        print(f" [{count}] failed to store {result.url}: {e}")

                    print(f" [{count}] {result.url} | Content Length: {len(result.markdown.raw_markdown)}")

                else:

                    error_msg = getattr(result , 'error_message' , 'Unkown error')  
                    print(f"[{count}] Error at {result.url}: {error_msg}")          

if __name__ == "__main__":
    asyncio.run(main()) 
