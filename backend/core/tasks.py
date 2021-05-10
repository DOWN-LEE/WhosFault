from __future__ import absolute_import
from celery import shared_task

from .tools.riotAPI import matchlist_async
from core.redis.Redis import RedisQueue
import asyncio


NUMS_BY_ONETIME = 10


@shared_task
def api_scheduler():
    rq = RedisQueue("matches")

    print("hello!")
    if rq.isEmpty():
        return

    #matchidlist = map(lambda x : x.decode(), rq.getlist(NUMS_BY_ONETIME))
    matchidlist = rq.getlist(NUMS_BY_ONETIME)

    asyncio.run(matchlist_async(matchidlist, rq))