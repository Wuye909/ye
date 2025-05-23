import scrapy
from asgiref.sync import sync_to_async
from copy import deepcopy
from lxml import etree
from scrapy import Selector
from spider_qunaer import items
from warehouse import models
import django

class QunaerSpider(scrapy.Spider):
    name = 'qunaer'
    start_urls = ['https://travel.qunar.com/p-cs300022-changsha-jingdian']
    page_num = 1
    spider_log_created = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        django.setup()

    @sync_to_async
    def create_spider_log(self):
        models.SpiderLog.objects.create()

    async def parse(self, response):
        if not self.spider_log_created:
            await self.create_spider_log()
            self.spider_log_created = True

        item_scenery = items.SpiderSceneryItem()
        scenery_list = response.xpath("//ul[@class='list_item clrfix']/li")
        for i in scenery_list:
            item_scenery["scenery_name"] = i.xpath("./div/div/a/span/text()").extract_first()
            item_scenery["rank"] = i.xpath("./div/div/div/span[2]/span/text()").extract_first()
            item_scenery["people_percent"] = i.xpath("./div/div[2]/span/span/text()").extract_first()

            scenery = await sync_to_async(models.Scenery.objects.filter(scenery_name=item_scenery["scenery_name"]).first)()
            if scenery:
                await sync_to_async(scenery.evaluates.all().delete)()
                await sync_to_async(scenery.delete)()

            detail_url = i.xpath("./a/@href").extract_first()
            if not await sync_to_async(models.Scenery.objects.filter(scenery_name=item_scenery["scenery_name"]).first)():
                yield scrapy.Request(
                    detail_url,
                    callback=self.get_detail,
                    meta={
                        "item_scenery": deepcopy(item_scenery),
                        "playwright": True,
                        "playwright_context": "new",
                        "playwright_page_methods": [
                            {"method": "wait_for_load_state", "args": ["networkidle"]},
                        ],
                    },
                    encoding="utf-8",
                    dont_filter=True
                )

        if self.page_num < 100:
            self.page_num += 1
            yield scrapy.Request(url=f"{self.start_urls[0]}-1-{self.page_num}", callback=self.parse)

    async def get_detail(self, response):
        item_scenery = response.meta["item_scenery"]
        score = response.xpath('//*[@id="js_mainleft"]/div[4]/div/div[2]/div[1]/div[1]/span[1]/text()').extract_first()
        if score:
            try:
                item_scenery["score"] = float(score)
            except Exception as e:
                print(f"score err: {score}")
                item_scenery["score"] = 0
        else:
            item_scenery["score"] = 0
        play_time = response.xpath('//div[@class="time"]/text()').extract_first()
        if play_time:
            item_scenery["play_time"] = play_time.split("：")[1]
        else:
            item_scenery["play_time"] = None
        city = response.xpath('//td[@class="td_l"]/dl[1]/dd/span/text()').extract_first()
        print(f"city: {city}")
        item_scenery["city"] = city

        yield item_scenery

        await self.get_evalute(response)
        i = 0
        for path in response.xpath("//div[@class='b_paging']/a"):
            if i >= 4:
                break
            evalute_path = path.xpath("./@href").extract_first()
            i += 1
            print("evalute_path:", evalute_path)
            yield scrapy.Request(
                evalute_path,
                callback=self.get_evalute,
                meta={
                    "item_scenery": deepcopy(item_scenery),
                    "playwright": True,
                    "playwright_context": "new",
                    "playwright_page_methods": [
                        {"method": "wait_for_load_state", "args": ["networkidle"]},
                    ],
                },
                encoding="utf-8",
                dont_filter=True
            )

    async def get_evalute(self, response):
        item_scenery = response.meta["item_scenery"]
        evalute_list = response.xpath("//ul[@id='comment_box']/li")
        if not evalute_list:
            return
        for evalute in evalute_list:
            item_evalute = items.SpiderEvaluteItem()
            item_evalute["content"] = evalute.xpath("./div[1]/div[1]/div[@class='e_comment_content']").xpath('string(.)').extract()[0].replace("阅读全部", "").replace("\n", "").replace("\r", "")
            item_evalute['send_time'] = evalute.xpath("./div[1]/div[1]/div[5]/ul/li[1]/text()").extract_first()
            item_evalute['user_name'] = evalute.xpath("./div[2]/div[2]/a/text()").extract_first()
            score = evalute.xpath("./div[1]/div[1]/div[2]/span/span/@class").extract_first()
            if score:
                score = score.split("star_")[-1]
            item_evalute['score'] = score if score else 0
            item_evalute['scenery_name'] = item_scenery['scenery_name']
            yield item_evalute