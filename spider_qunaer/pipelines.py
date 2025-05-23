from warehouse import models
from asgiref.sync import sync_to_async
from spider_qunaer import items

class SpiderQunaerPipeline:
    @sync_to_async
    def process_scenery(self, item):
        scenery, created = models.Scenery.objects.get_or_create(
            scenery_name=item['scenery_name'],
            defaults={
                'rank': item.get('rank'),
                'people_percent': item.get('people_percent'),
                'score': item.get('score', 0),
                'play_time': item.get('play_time'),
                'city': item.get('city')
            }
        )
        return scenery

    @sync_to_async
    def process_evalute(self, item, scenery):
        evalute = models.Evaluate.objects.create(
            content=item['content'],
            send_time=item['send_time'],
            user_name=item['user_name'],
            score=item['score'],
            scenery=scenery
        )
        return evalute

    # spider_qunaer/pipelines.py
    async def process_item(self, item, spider):
        try:
            if isinstance(item, items.SpiderSceneryItem):
                scenery = await self.process_scenery(item)
            elif isinstance(item, items.SpiderEvaluteItem):
                scenery = await sync_to_async(models.Scenery.objects.filter(scenery_name=item['scenery_name']).first)()
                if scenery:
                    await self.process_evalute(item, scenery)
                else:
                    spider.logger.warning(f"No scenery found for {item['scenery_name']}")
            return item
        except Exception as e:
            spider.logger.error(f"Pipeline error for item {item}: {e}")
            raise

    @sync_to_async
    def process_evalute(self, item, scenery):
        evaluate = models.Evaluate.objects.create(
            content=item['content'],
            send_time=item['send_time'],
            user_name=item['user_name'],
            score=item['score'],
            scenery_name=item['scenery_name']
        )
        scenery.evaluates.add(evaluate)
        return evaluate